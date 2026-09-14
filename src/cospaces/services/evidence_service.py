"""T7 local evidence bundle creation and independent validation."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from cospaces import __version__
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.evidence import (
    EvidenceCreateRecord,
    EvidenceItemRecord,
    EvidenceManifest,
    EvidenceValidationRecord,
)
from cospaces.domain.results import utc_now
from cospaces.evidence_config import EvidenceItem, load_evidence_plan

_RECORD_KINDS = frozenset({"checkpoint", "fixture", "run", "verification"})
_SECRET_COMPONENTS = frozenset({".ssh", ".gnupg", ".aws", ".azure", ".kube"})
_SECRET_FILENAMES = frozenset(
    {
        ".git-credentials",
        ".netrc",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
    }
)
_SECRET_MARKERS = (
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN DSA PRIVATE KEY-----",
    b"-----BEGIN PRIVATE KEY-----",
    b"github_pat_",
    b"ghp_",
    b"gho_",
    b"ghs_",
    b"ghu_",
    b"ghr_",
)
_SCAN_CHUNK = 64 * 1024


@dataclass(frozen=True)
class EvidenceCreateRequest:
    plan: str
    root: Path = Path(".")
    output_directory: str | None = None


@dataclass(frozen=True)
class EvidenceValidateRequest:
    bundle: Path
    root: Path = Path(".")


@dataclass(frozen=True)
class EvidenceCreateActionResult:
    record: EvidenceCreateRecord | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.record is not None and self.failure is None


@dataclass(frozen=True)
class EvidenceValidationActionResult:
    record: EvidenceValidationRecord | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.record is not None and self.failure is None and self.record.valid


def _failure(
    code: str,
    message: str,
    kind: FailureKind = FailureKind.PERSISTENCE,
) -> DomainFailure:
    return DomainFailure(code=code, kind=kind, message=message)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _forbidden_path(path: PurePosixPath) -> bool:
    parts = [part.lower() for part in path.parts]
    if any(part in _SECRET_COMPONENTS for part in parts):
        return True
    name = path.name.lower()
    if name in _SECRET_FILENAMES or name == ".env" or name.startswith(".env."):
        return True
    return any(
        part == ".git" and parts[index + 1] in {"config", "credentials"}
        for index, part in enumerate(parts[:-1])
    )


def _contains_secret_marker(path: Path) -> bool:
    overlap = max(len(marker) for marker in _SECRET_MARKERS) - 1
    previous = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_SCAN_CHUNK)
            if not chunk:
                return False
            data = previous + chunk
            if any(marker in data for marker in _SECRET_MARKERS):
                return True
            previous = data[-overlap:] if overlap else b""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_SCAN_CHUNK)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def _safe_output_directory(root: Path, relative: str) -> Path | DomainFailure:
    raw = PurePosixPath(relative)
    unsafe = raw.is_absolute() or ".." in raw.parts or "\\" in relative or "\x00" in relative
    if unsafe or _forbidden_path(raw):
        return _failure(
            "evidence_unsafe_output_path",
            "Evidence output directory must be a safe repository-relative path",
            FailureKind.USAGE,
        )
    candidate = root.joinpath(*raw.parts)
    ancestor = candidate
    while not ancestor.exists() and ancestor != root:
        ancestor = ancestor.parent
    try:
        ancestor_real = ancestor.resolve(strict=True)
    except OSError:
        return _failure("evidence_output_failed", "Cannot resolve evidence output parent")
    if not _inside(ancestor_real, root):
        return _failure(
            "evidence_unsafe_output_path",
            "Evidence output directory escapes root",
        )
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        real = candidate.resolve(strict=True)
    except OSError:
        return _failure("evidence_output_failed", "Cannot create evidence output directory")
    if not real.is_dir() or not _inside(real, root):
        return _failure(
            "evidence_unsafe_output_path",
            "Evidence output directory escapes root",
        )
    try:
        resolved_relative = real.relative_to(root)
    except ValueError:
        return _failure(
            "evidence_unsafe_output_path",
            "Evidence output directory escapes root",
        )
    if _forbidden_path(PurePosixPath(resolved_relative.as_posix())):
        return _failure(
            "evidence_unsafe_output_path",
            "Evidence output directory resolves into a secret-prone path",
        )
    return real


def _record_payload(
    raw: object,
) -> tuple[dict[str, object] | None, str | None, str | None]:
    if not isinstance(raw, dict):
        return None, None, None
    schema = raw.get("schema") if isinstance(raw.get("schema"), str) else None
    operation = raw.get("operation") if isinstance(raw.get("operation"), str) else None
    if schema == "cospaces.result/v1" and isinstance(raw.get("result"), dict):
        nested = raw["result"]
        nested_schema = nested.get("schema")
        nested_schema = nested_schema if isinstance(nested_schema, str) else None
        merged = dict(nested)
        if "workspace" not in merged and isinstance(raw.get("workspace"), dict):
            merged["workspace"] = raw["workspace"]
        return merged, nested_schema or schema, operation
    return raw, schema, operation


def _record_provenance(
    path: Path,
    kind: str,
) -> tuple[str | None, dict[str, object] | None] | DomainFailure:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _failure(
            "evidence_record_invalid",
            f"Declared {kind} record is not valid JSON",
        )
    payload, source_schema, operation = _record_payload(raw)
    if payload is None:
        return _failure(
            "evidence_record_invalid",
            f"Declared {kind} record is not a JSON object",
        )
    if kind == "fixture" and source_schema != "cospaces.fixture/v1":
        return _failure(
            "evidence_record_invalid",
            "Fixture item is not cospaces.fixture/v1",
        )
    if kind == "verification" and source_schema != "cospaces.verify/v1":
        return _failure(
            "evidence_record_invalid",
            "Verification item is not cospaces.verify/v1",
        )
    if kind == "checkpoint" and source_schema != "cospaces.checkpoint/v1":
        return _failure(
            "evidence_record_invalid",
            "Checkpoint item is not cospaces.checkpoint/v1",
        )
    if kind == "run" and not (operation == "run" or isinstance(payload.get("run_id"), str)):
        return _failure(
            "evidence_record_invalid",
            "Run item does not contain a run record",
        )

    provenance: dict[str, object] = {}
    scalar_keys = (
        "repository",
        "ref",
        "head",
        "task_id",
        "correlation_id",
        "run_id",
        "verification_id",
        "fixture_run_id",
        "task_run_id",
    )
    for key in scalar_keys:
        value = payload.get(key)
        if value is not None:
            provenance[key] = value
    workspace = payload.get("workspace")
    if isinstance(workspace, dict):
        bounded = {
            key: workspace[key]
            for key in ("name", "repository", "ref", "machine")
            if workspace.get(key) is not None
        }
        if bounded:
            provenance["workspace"] = bounded
    records = payload.get("records")
    if isinstance(records, dict):
        refs = {
            key: records[key]
            for key in ("last_run_id", "last_verification_id")
            if records.get(key) is not None
        }
        if refs:
            provenance["record_references"] = refs
    support = payload.get("support_run_ids")
    if isinstance(support, list) and all(isinstance(item, str) for item in support):
        provenance["support_run_ids"] = support
    return source_schema, provenance or None


def _manifest_json(manifest: EvidenceManifest) -> str:
    data = manifest.to_dict()
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


class EvidenceService:
    def create(self, request: EvidenceCreateRequest) -> EvidenceCreateActionResult:
        configured = load_evidence_plan(request.root, request.plan)
        if not configured.ok:
            return EvidenceCreateActionResult(failure=configured.failure)
        plan = configured.plan
        assert plan is not None
        try:
            root = request.root.resolve(strict=True)
        except OSError:
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_root_unavailable",
                    "Evidence root does not exist",
                )
            )
        if not root.is_dir():
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_root_unavailable",
                    "Evidence root is not a directory",
                )
            )

        capture_candidate = root.joinpath(*PurePosixPath(plan.capture_root).parts)
        try:
            capture_root = capture_candidate.resolve(strict=True)
        except OSError:
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_capture_root_unavailable",
                    "Capture root does not exist",
                )
            )
        if not capture_root.is_dir() or not _inside(capture_root, root):
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_unsafe_capture_root",
                    "Capture root escapes repository root",
                )
            )
        try:
            capture_relative = capture_root.relative_to(root)
        except ValueError:
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_unsafe_capture_root",
                    "Capture root escapes repository root",
                )
            )
        if _forbidden_path(PurePosixPath(capture_relative.as_posix())):
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_secret_path_rejected",
                    "Capture root resolves into a secret-prone path",
                )
            )

        output_relative = request.output_directory or plan.output_directory
        output = _safe_output_directory(root, output_relative)
        if isinstance(output, DomainFailure):
            return EvidenceCreateActionResult(failure=output)

        evidence_id = str(uuid4())
        final_bundle = output / evidence_id
        if final_bundle.exists():
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_bundle_exists",
                    "Generated evidence bundle already exists",
                )
            )
        temporary = Path(tempfile.mkdtemp(prefix=".tmp-evidence-", dir=output))
        files_dir = temporary / "files"
        files_dir.mkdir()
        item_records: list[EvidenceItemRecord] = []
        total_bytes = 0
        try:
            for index, item in enumerate(plan.items):
                captured = self._capture_item(
                    item=item,
                    index=index,
                    capture_root=capture_root,
                    files_dir=files_dir,
                    total_before=total_bytes,
                    max_total=plan.max_total_bytes,
                )
                if isinstance(captured, DomainFailure):
                    return EvidenceCreateActionResult(failure=captured)
                record, captured_bytes = captured
                total_bytes += captured_bytes
                item_records.append(record)

            manifest = EvidenceManifest(
                evidence_id=evidence_id,
                plan=plan.name,
                created_at=utc_now(),
                controller_version=__version__,
                capture_root=plan.capture_root,
                items=tuple(item_records),
                notes=plan.notes,
                total_captured_bytes=total_bytes,
            )
            manifest_path = temporary / "manifest.json"
            manifest_path.write_text(_manifest_json(manifest), encoding="utf-8")
            os.replace(temporary, final_bundle)
            return EvidenceCreateActionResult(
                record=EvidenceCreateRecord(
                    evidence_id=evidence_id,
                    plan=plan.name,
                    bundle_path=_display_path(final_bundle, root),
                    manifest=manifest,
                )
            )
        except OSError as exc:
            return EvidenceCreateActionResult(
                failure=_failure(
                    "evidence_write_failed",
                    f"Evidence capture failed: {exc.__class__.__name__}",
                )
            )
        finally:
            if temporary.exists():
                shutil.rmtree(temporary, ignore_errors=True)

    def _capture_item(
        self,
        *,
        item: EvidenceItem,
        index: int,
        capture_root: Path,
        files_dir: Path,
        total_before: int,
        max_total: int,
    ) -> tuple[EvidenceItemRecord, int] | DomainFailure:
        source_rel = PurePosixPath(item.path)
        if _forbidden_path(source_rel):
            return _failure(
                "evidence_secret_path_rejected",
                f"Secret-prone path rejected: {item.path}",
            )
        candidate = capture_root.joinpath(*source_rel.parts)
        if not candidate.exists():
            if item.required:
                return _failure(
                    "evidence_required_missing",
                    f"Required evidence file missing: {item.path}",
                )
            record = EvidenceItemRecord(
                index=index,
                kind=item.kind,
                source_path=item.path,
                stored_path=None,
                required=False,
                status="missing_optional",
                size_bytes=None,
                sha256=None,
                content_type=None,
                source_schema=None,
                provenance=None,
            )
            return record, 0
        try:
            source = candidate.resolve(strict=True)
        except OSError:
            return _failure(
                "evidence_read_failed",
                f"Cannot resolve evidence file: {item.path}",
            )
        if not _inside(source, capture_root):
            return _failure(
                "evidence_symlink_escape",
                f"Evidence path escapes capture root: {item.path}",
            )
        resolved_rel = source.relative_to(capture_root)
        if _forbidden_path(PurePosixPath(resolved_rel.as_posix())):
            return _failure(
                "evidence_secret_path_rejected",
                f"Secret-prone target rejected: {item.path}",
            )
        if not source.is_file():
            return _failure(
                "evidence_not_regular_file",
                f"Evidence item is not a regular file: {item.path}",
            )
        try:
            size = source.stat().st_size
        except OSError:
            return _failure(
                "evidence_read_failed",
                f"Cannot stat evidence file: {item.path}",
            )
        if size > item.max_bytes:
            return _failure(
                "evidence_item_too_large",
                f"Evidence file exceeds max_bytes: {item.path}",
            )
        if total_before + size > max_total:
            return _failure(
                "evidence_total_too_large",
                "Evidence plan exceeds max_total_bytes",
            )
        try:
            if _contains_secret_marker(source):
                return _failure(
                    "evidence_secret_material_detected",
                    f"Secret-like material detected in evidence file: {item.path}",
                )
        except OSError:
            return _failure(
                "evidence_read_failed",
                f"Cannot scan evidence file: {item.path}",
            )

        destination = files_dir / f"{index:04d}"
        try:
            shutil.copyfile(source, destination)
            destination_size = destination.stat().st_size
        except OSError:
            return _failure(
                "evidence_write_failed",
                f"Cannot copy evidence file: {item.path}",
            )
        if destination_size > item.max_bytes:
            return _failure(
                "evidence_size_changed",
                f"Evidence file changed size during capture: {item.path}",
            )
        if total_before + destination_size > max_total:
            return _failure(
                "evidence_size_changed",
                f"Evidence file changed size during capture: {item.path}",
            )
        try:
            if _contains_secret_marker(destination):
                return _failure(
                    "evidence_secret_material_detected",
                    f"Secret-like material detected in captured bytes: {item.path}",
                )
            digest = _sha256(destination)
        except OSError:
            return _failure(
                "evidence_hash_failed",
                f"Cannot scan/hash captured evidence file: {item.path}",
            )

        source_schema: str | None = None
        provenance: dict[str, object] | None = None
        if item.kind in _RECORD_KINDS:
            parsed = _record_provenance(destination, item.kind)
            if isinstance(parsed, DomainFailure):
                return parsed
            source_schema, provenance = parsed
        content_type = mimetypes.guess_type(item.path)[0] or "application/octet-stream"
        record = EvidenceItemRecord(
            index=index,
            kind=item.kind,
            source_path=item.path,
            stored_path=f"files/{index:04d}",
            required=item.required,
            status="captured",
            size_bytes=destination_size,
            sha256=digest,
            content_type=content_type,
            source_schema=source_schema,
            provenance=provenance,
        )
        return record, destination_size

    def validate(
        self,
        request: EvidenceValidateRequest,
    ) -> EvidenceValidationActionResult:
        try:
            root = request.root.resolve(strict=True)
            bundle = request.bundle
            if not bundle.is_absolute():
                bundle = root / bundle
            if bundle.is_symlink():
                raise ValueError("bundle symlink")
            bundle = bundle.resolve(strict=True)
        except (OSError, ValueError):
            return EvidenceValidationActionResult(
                failure=_failure(
                    "evidence_bundle_unavailable",
                    "Evidence bundle cannot be resolved safely",
                    FailureKind.VERIFICATION,
                )
            )
        if not bundle.is_dir():
            return self._validation_failure("Evidence bundle is not a directory")
        manifest_path = bundle / "manifest.json"
        if manifest_path.is_symlink():
            return self._validation_failure("Manifest must not be a symlink")
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return EvidenceValidationActionResult(
                failure=_failure(
                    "evidence_manifest_invalid",
                    "Evidence manifest is missing or malformed",
                    FailureKind.VERIFICATION,
                )
            )
        if not isinstance(raw, dict) or raw.get("schema") != "cospaces.evidence/v1":
            return EvidenceValidationActionResult(
                failure=_failure(
                    "evidence_manifest_invalid",
                    "Unsupported evidence manifest schema",
                    FailureKind.VERIFICATION,
                )
            )
        raw_id = raw.get("evidence_id")
        evidence_id = raw_id if isinstance(raw_id, str) else None
        items = raw.get("items")
        if evidence_id is None or not isinstance(items, list) or len(items) > 256:
            return EvidenceValidationActionResult(
                failure=_failure(
                    "evidence_manifest_invalid",
                    "Evidence manifest structure is invalid",
                    FailureKind.VERIFICATION,
                )
            )

        expected_files: set[str] = set()
        checked = 0
        for item in items:
            checked_result = self._validate_manifest_item(bundle, item)
            if isinstance(checked_result, EvidenceValidationActionResult):
                return checked_result
            stored_path = checked_result
            if stored_path is not None:
                expected_files.add(stored_path)
                checked += 1

        actual_files: set[str] = set()
        for child in bundle.rglob("*"):
            if child.is_symlink():
                return self._validation_failure("Evidence bundle contains a symlink")
            if not child.is_file() or child == manifest_path:
                continue
            actual_files.add(child.relative_to(bundle).as_posix())
        if actual_files != expected_files:
            return self._validation_failure("Evidence bundle contains missing or unexpected files")

        return EvidenceValidationActionResult(
            record=EvidenceValidationRecord(
                bundle_path=_display_path(bundle, root),
                evidence_id=evidence_id,
                valid=True,
                checked_files=checked,
            )
        )

    def _validate_manifest_item(
        self,
        bundle: Path,
        item: object,
    ) -> str | None | EvidenceValidationActionResult:
        if not isinstance(item, dict):
            return self._validation_failure("Evidence item manifest entry is invalid")
        status = item.get("status")
        stored_path = item.get("stored_path")
        if status == "missing_optional":
            if stored_path is not None:
                return self._validation_failure(
                    "Missing optional item unexpectedly has stored_path"
                )
            return None
        if status != "captured" or not isinstance(stored_path, str):
            return self._validation_failure("Evidence item status/stored_path is invalid")
        pure = PurePosixPath(stored_path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in stored_path:
            return self._validation_failure("Evidence stored path is unsafe")
        candidate = bundle.joinpath(*pure.parts)
        if candidate.is_symlink():
            return self._validation_failure("Evidence stored file must not be a symlink")
        try:
            target = candidate.resolve(strict=True)
        except OSError:
            return self._validation_failure("Evidence stored file is missing")
        if not _inside(target, bundle) or not target.is_file():
            return self._validation_failure("Evidence stored file escapes bundle or is not regular")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        if not isinstance(size, int) or size < 0 or not isinstance(digest, str):
            return self._validation_failure("Evidence item size/hash metadata is invalid")
        try:
            if target.stat().st_size != size or _sha256(target) != digest:
                return self._validation_failure("Evidence file hash or size mismatch")
            if _contains_secret_marker(target):
                return self._validation_failure(
                    "Evidence file contains rejected secret-like material"
                )
        except OSError:
            return self._validation_failure("Evidence file could not be read during validation")
        return pure.as_posix()

    @staticmethod
    def _validation_failure(message: str) -> EvidenceValidationActionResult:
        return EvidenceValidationActionResult(
            failure=_failure(
                "evidence_bundle_invalid",
                message,
                FailureKind.VERIFICATION,
            )
        )
