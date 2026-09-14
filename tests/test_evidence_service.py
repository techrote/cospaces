import hashlib
import json
from pathlib import Path

from cospaces.services.evidence_service import (
    EvidenceCreateRequest,
    EvidenceService,
    EvidenceValidateRequest,
)


def write_plan(tmp_path: Path, items: str, *, capture_root: str = "capture") -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[evidence.default]\n"
        f'capture_root = "{capture_root}"\n'
        'output_directory = "bundles"\n'
        "max_total_bytes = 1000000\n"
        'notes = ["public-safe test bundle"]\n' + items,
        encoding="utf-8",
    )


def fixture_record() -> dict[str, object]:
    return {
        "schema": "cospaces.fixture/v1",
        "fixture_run_id": "fixture-run",
        "task_run_id": "task-run",
        "support_run_ids": ["head-run", "output-run"],
        "repository": "owner/repo",
        "ref": "main",
        "head": "a" * 40,
        "workspace": {
            "name": "space-one",
            "repository": "owner/repo",
            "ref": "main",
            "machine": "standard",
        },
    }


def test_create_bundle_captures_hashes_provenance_and_optional_omission(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    fixture = capture / "fixture.json"
    fixture.write_text(json.dumps(fixture_record()), encoding="utf-8")
    artifact = capture / "artifact.bin"
    artifact.write_bytes(b"artifact-bytes")
    write_plan(
        tmp_path,
        "[[evidence.default.items]]\n"
        'path = "fixture.json"\n'
        'kind = "fixture"\n'
        "[[evidence.default.items]]\n"
        'path = "artifact.bin"\n'
        'kind = "artifact"\n'
        "[[evidence.default.items]]\n"
        'path = "optional.log"\n'
        'kind = "log"\n'
        "required = false\n",
    )

    service = EvidenceService()
    result = service.create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert result.ok
    assert result.record is not None
    record = result.record
    assert record.schema == "cospaces.evidence/v1"
    bundle = tmp_path / record.bundle_path
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "cospaces.evidence/v1"
    assert manifest["controller_version"] == "0.0.1"
    assert [item["status"] for item in manifest["items"]] == [
        "captured",
        "captured",
        "missing_optional",
    ]
    first = manifest["items"][0]
    assert first["source_schema"] == "cospaces.fixture/v1"
    assert first["provenance"]["head"] == "a" * 40
    assert first["provenance"]["workspace"]["name"] == "space-one"
    second = manifest["items"][1]
    copied = bundle / second["stored_path"]
    assert copied.read_bytes() == b"artifact-bytes"
    assert second["sha256"] == hashlib.sha256(b"artifact-bytes").hexdigest()
    assert second["size_bytes"] == len(b"artifact-bytes")
    assert manifest["total_captured_bytes"] == fixture.stat().st_size + artifact.stat().st_size

    validated = service.validate(EvidenceValidateRequest(bundle=bundle, root=tmp_path))
    assert validated.ok
    assert validated.record is not None
    assert validated.record.valid is True
    assert validated.record.checked_files == 2


def test_missing_required_file_fails_without_final_bundle(tmp_path: Path) -> None:
    (tmp_path / "capture").mkdir()
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = "missing.bin"\nkind = "artifact"\n',
    )

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_required_missing"
    bundles = tmp_path / "bundles"
    assert bundles.is_dir()
    assert list(bundles.iterdir()) == []


def test_secret_prone_path_is_rejected(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / ".env").write_text("SAFE_FOR_TEST=true\n", encoding="utf-8")
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = ".env"\nkind = "artifact"\n',
    )

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_secret_path_rejected"


def test_secret_material_marker_is_rejected(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "log.txt").write_text("prefix ghp_not-a-real-token suffix\n", encoding="utf-8")
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = "log.txt"\nkind = "log"\n',
    )

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_secret_material_detected"


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = capture / "link.txt"
    link.symlink_to(outside)
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = "link.txt"\nkind = "artifact"\n',
    )

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_symlink_escape"


def test_capture_root_cannot_be_secret_prone_directory(tmp_path: Path) -> None:
    secret_root = tmp_path / ".ssh"
    secret_root.mkdir()
    (secret_root / "known_hosts").write_text("example", encoding="utf-8")
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = "known_hosts"\nkind = "artifact"\n',
        capture_root=".ssh",
    )

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_secret_path_rejected"


def test_tampering_is_detected_by_independent_validation(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "artifact.bin").write_bytes(b"original")
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = "artifact.bin"\nkind = "artifact"\n',
    )
    service = EvidenceService()
    created = service.create(EvidenceCreateRequest(plan="default", root=tmp_path))
    assert created.record is not None
    bundle = tmp_path / created.record.bundle_path
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    stored = bundle / manifest["items"][0]["stored_path"]
    stored.write_bytes(b"tampered")

    validated = service.validate(EvidenceValidateRequest(bundle=bundle, root=tmp_path))

    assert not validated.ok
    assert validated.failure is not None
    assert validated.failure.code == "evidence_bundle_invalid"
    assert int(validated.failure.exit_status) == 7


def test_declared_fixture_record_must_match_schema(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "fixture.json").write_text('{"schema":"wrong/v1"}\n', encoding="utf-8")
    write_plan(
        tmp_path,
        '[[evidence.default.items]]\npath = "fixture.json"\nkind = "fixture"\n',
    )

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_record_invalid"
