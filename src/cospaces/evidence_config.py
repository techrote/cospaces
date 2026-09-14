"""Repository-controlled T7 evidence plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .config import load_config
from .domain.contracts import DomainFailure, FailureKind

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ALLOWED_KINDS = frozenset(
    {"artifact", "checkpoint", "fixture", "log", "other", "run", "verification"}
)
_SECRET_COMPONENTS = frozenset({".ssh", ".gnupg", ".aws", ".azure", ".kube"})
_SECRET_FILENAMES = frozenset(
    {".git-credentials", ".netrc", "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"}
)
_NOTE_SECRET_MARKERS = (
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----",
    "github_pat_",
    "ghp_",
    "gho_",
    "ghs_",
    "ghu_",
    "ghr_",
)
_DEFAULT_ITEM_MAX_BYTES = 50 * 1024 * 1024
_MAX_ITEM_BYTES = 1024 * 1024 * 1024
_DEFAULT_TOTAL_BYTES = 100 * 1024 * 1024
_MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
_MAX_ITEMS = 256
_MAX_NOTES = 64


@dataclass(frozen=True)
class EvidenceItem:
    path: str
    kind: str
    required: bool = True
    max_bytes: int = _DEFAULT_ITEM_MAX_BYTES


@dataclass(frozen=True)
class EvidencePlan:
    name: str
    capture_root: str
    output_directory: str
    max_total_bytes: int
    notes: tuple[str, ...]
    items: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class EvidenceConfigResult:
    plan: EvidencePlan | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.plan is not None and self.failure is None


def _failure(code: str, message: str) -> EvidenceConfigResult:
    return EvidenceConfigResult(
        failure=DomainFailure(code=code, kind=FailureKind.USAGE, message=message)
    )


def _secret_prone_path(value: str) -> bool:
    path = PurePosixPath(value)
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


def _relative_path(value: Any, field: str) -> str | DomainFailure:
    if not isinstance(value, str) or not value or len(value) > 512 or "\x00" in value:
        return DomainFailure(
            code="invalid_evidence_plan",
            kind=FailureKind.USAGE,
            message=f"{field} must be a bounded relative POSIX path",
        )
    if "\\" in value:
        return DomainFailure(
            code="invalid_evidence_plan",
            kind=FailureKind.USAGE,
            message=f"{field} must use POSIX path separators",
        )
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return DomainFailure(
            code="invalid_evidence_plan",
            kind=FailureKind.USAGE,
            message=f"{field} must remain within its approved root",
        )
    return value


def _positive_int(value: Any, *, default: int, maximum: int, field: str) -> int | DomainFailure:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        return DomainFailure(
            code="invalid_evidence_plan",
            kind=FailureKind.USAGE,
            message=f"{field} must be an integer",
        )
    if value <= 0 or value > maximum:
        return DomainFailure(
            code="invalid_evidence_plan",
            kind=FailureKind.USAGE,
            message=f"{field} must be within [1, {maximum}]",
        )
    return value


def load_evidence_plan(root: str | Path, name: str) -> EvidenceConfigResult:
    if _NAME_RE.fullmatch(name) is None:
        return _failure("invalid_evidence_plan_name", "evidence plan name must be a bounded identifier")
    loaded = load_config(Path(root) / ".cospaces.toml")
    if not loaded.ok:
        return EvidenceConfigResult(failure=loaded.failure)
    assert loaded.config is not None
    section = loaded.config.extra_sections.get("evidence")
    if not isinstance(section, dict) or name not in section:
        return _failure("evidence_plan_not_found", f"evidence plan not found: {name}")
    raw = section[name]
    if not isinstance(raw, dict):
        return _failure("invalid_evidence_plan", f"evidence.{name} must be a table")
    unknown = sorted(
        set(raw) - {"capture_root", "output_directory", "max_total_bytes", "notes", "items"}
    )
    if unknown:
        return _failure(
            "invalid_evidence_plan",
            f"evidence.{name} contains unsupported keys: {', '.join(unknown)}",
        )

    capture_root = _relative_path(raw.get("capture_root", "."), "capture_root")
    if isinstance(capture_root, DomainFailure):
        return EvidenceConfigResult(failure=capture_root)
    if _secret_prone_path(capture_root):
        return _failure("evidence_secret_path_rejected", "capture_root is secret-prone")
    output_directory = _relative_path(
        raw.get("output_directory", ".cospaces/evidence"), "output_directory"
    )
    if isinstance(output_directory, DomainFailure):
        return EvidenceConfigResult(failure=output_directory)
    if _secret_prone_path(output_directory):
        return _failure("evidence_secret_path_rejected", "output_directory is secret-prone")
    max_total = _positive_int(
        raw.get("max_total_bytes"),
        default=_DEFAULT_TOTAL_BYTES,
        maximum=_MAX_TOTAL_BYTES,
        field="max_total_bytes",
    )
    if isinstance(max_total, DomainFailure):
        return EvidenceConfigResult(failure=max_total)

    notes_raw = raw.get("notes", [])
    if (
        not isinstance(notes_raw, list)
        or len(notes_raw) > _MAX_NOTES
        or not all(isinstance(item, str) and len(item) <= 1000 for item in notes_raw)
    ):
        return _failure("invalid_evidence_plan", "notes must be a bounded list of strings")
    if any(marker in note for note in notes_raw for marker in _NOTE_SECRET_MARKERS):
        return _failure("evidence_secret_material_detected", "Evidence notes contain secret-like material")

    items_raw = raw.get("items", [])
    if not isinstance(items_raw, list) or not items_raw or len(items_raw) > _MAX_ITEMS:
        return _failure(
            "invalid_evidence_plan",
            f"items must be a non-empty list of at most {_MAX_ITEMS} tables",
        )
    items: list[EvidenceItem] = []
    for index, item in enumerate(items_raw):
        if not isinstance(item, dict):
            return _failure("invalid_evidence_plan", f"items[{index}] must be a table")
        item_unknown = sorted(set(item) - {"path", "kind", "required", "max_bytes"})
        if item_unknown:
            return _failure(
                "invalid_evidence_plan",
                f"items[{index}] contains unsupported keys: {', '.join(item_unknown)}",
            )
        path = _relative_path(item.get("path"), f"items[{index}].path")
        if isinstance(path, DomainFailure):
            return EvidenceConfigResult(failure=path)
        if _secret_prone_path(path):
            return _failure("evidence_secret_path_rejected", f"items[{index}].path is secret-prone")
        kind = item.get("kind", "artifact")
        if kind not in _ALLOWED_KINDS:
            return _failure(
                "invalid_evidence_plan",
                f"items[{index}].kind must be one of: {', '.join(sorted(_ALLOWED_KINDS))}",
            )
        required = item.get("required", True)
        if not isinstance(required, bool):
            return _failure("invalid_evidence_plan", f"items[{index}].required must be boolean")
        max_bytes = _positive_int(
            item.get("max_bytes"),
            default=_DEFAULT_ITEM_MAX_BYTES,
            maximum=_MAX_ITEM_BYTES,
            field=f"items[{index}].max_bytes",
        )
        if isinstance(max_bytes, DomainFailure):
            return EvidenceConfigResult(failure=max_bytes)
        items.append(EvidenceItem(path=path, kind=kind, required=required, max_bytes=max_bytes))

    return EvidenceConfigResult(
        plan=EvidencePlan(
            name=name,
            capture_root=capture_root,
            output_directory=output_directory,
            max_total_bytes=max_total,
            notes=tuple(notes_raw),
            items=tuple(items),
        )
    )
