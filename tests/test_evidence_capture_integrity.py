import json
from pathlib import Path

import cospaces.services.evidence_service as evidence_service
from cospaces.services.evidence_service import (
    EvidenceCreateRequest,
    EvidenceService,
    EvidenceValidateRequest,
)


def write_plan(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[evidence.default]\n"
        'capture_root = "capture"\n'
        'output_directory = "bundles"\n'
        "[[evidence.default.items]]\n"
        'path = "artifact.bin"\n'
        'kind = "artifact"\n',
        encoding="utf-8",
    )


def test_destination_bytes_are_scanned_after_copy(tmp_path: Path, monkeypatch) -> None:
    capture = tmp_path / "capture"
    capture.mkdir()
    source = capture / "artifact.bin"
    source.write_bytes(b"safe-source")
    write_plan(tmp_path)

    original_copyfile = evidence_service.shutil.copyfile

    def mutating_copyfile(src, dst):
        result = original_copyfile(src, dst)
        Path(dst).write_bytes(b"ghp_not-a-real-token")
        return result

    monkeypatch.setattr(evidence_service.shutil, "copyfile", mutating_copyfile)

    result = EvidenceService().create(EvidenceCreateRequest(plan="default", root=tmp_path))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_secret_material_detected"


def test_validator_rejects_unexpected_root_file(tmp_path: Path) -> None:
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
    (bundle / "unexpected.txt").write_text("unexpected", encoding="utf-8")

    validated = service.validate(EvidenceValidateRequest(bundle=bundle, root=tmp_path))

    assert not validated.ok
    assert validated.failure is not None
    assert validated.failure.code == "evidence_bundle_invalid"
