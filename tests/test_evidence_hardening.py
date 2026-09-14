import json
from pathlib import Path

from cospaces.evidence_config import load_evidence_plan
from cospaces.services.evidence_service import (
    EvidenceCreateRequest,
    EvidenceService,
    EvidenceValidateRequest,
)


def write_plan(
    tmp_path: Path,
    *,
    capture_root: str = "capture",
    output_directory: str = "bundles",
    notes: str = "public-safe note",
    item_path: str = "artifact.bin",
) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[evidence.default]\n"
        f'capture_root = "{capture_root}"\n'
        f'output_directory = "{output_directory}"\n'
        f'notes = ["{notes}"]\n'
        "[[evidence.default.items]]\n"
        f'path = "{item_path}"\n'
        'kind = "artifact"\n',
        encoding="utf-8",
    )


def test_plan_rejects_secret_like_notes(tmp_path: Path) -> None:
    write_plan(tmp_path, notes="github_pat_not-a-real-token")

    result = load_evidence_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_secret_material_detected"


def test_directory_capture_is_rejected(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "directory").mkdir()
    write_plan(tmp_path, item_path="directory")

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_not_regular_file"


def test_capture_root_symlink_into_secret_directory_is_rejected(tmp_path: Path) -> None:
    secret = tmp_path / ".ssh"
    secret.mkdir()
    (secret / "known_hosts").write_text("example", encoding="utf-8")
    (tmp_path / "capture").symlink_to(secret, target_is_directory=True)
    write_plan(tmp_path, item_path="known_hosts")

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_secret_path_rejected"


def test_cli_output_override_cannot_target_secret_directory(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "artifact.bin").write_bytes(b"data")
    write_plan(tmp_path)

    result = EvidenceService().create(
        EvidenceCreateRequest(
            plan="default",
            root=tmp_path,
            output_directory=".ssh/evidence",
        )
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_unsafe_output_path"


def test_validator_rejects_unexpected_file_added_after_capture(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "artifact.bin").write_bytes(b"data")
    write_plan(tmp_path)
    service = EvidenceService()
    created = service.create(EvidenceCreateRequest(plan="default", root=tmp_path))
    assert created.record is not None
    bundle = tmp_path / created.record.bundle_path
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["items"][0]["status"] == "captured"
    (bundle / "files" / "extra").write_bytes(b"unexpected")

    validated = service.validate(EvidenceValidateRequest(bundle=bundle, root=tmp_path))

    assert not validated.ok
    assert validated.failure is not None
    assert validated.failure.code == "evidence_bundle_invalid"
