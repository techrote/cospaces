import argparse
import json

from cospaces.domain.evidence import (
    EvidenceCreateRecord,
    EvidenceItemRecord,
    EvidenceManifest,
    EvidenceValidationRecord,
)
from cospaces.evidence_output import emit_evidence_create, emit_evidence_validation
from cospaces.services.evidence_service import (
    EvidenceCreateActionResult,
    EvidenceValidationActionResult,
)


def test_evidence_create_json_uses_result_envelope(capsys) -> None:
    manifest = EvidenceManifest(
        evidence_id="evidence-id",
        plan="default",
        created_at="2026-09-14T00:00:00Z",
        controller_version="0.0.1",
        capture_root=".",
        items=(
            EvidenceItemRecord(
                index=0,
                kind="artifact",
                source_path="artifact.bin",
                stored_path="files/0000",
                required=True,
                status="captured",
                size_bytes=4,
                sha256="a" * 64,
                content_type="application/octet-stream",
                source_schema=None,
                provenance=None,
            ),
        ),
        notes=(),
        total_captured_bytes=4,
    )
    record = EvidenceCreateRecord(
        evidence_id="evidence-id",
        plan="default",
        bundle_path=".cospaces/evidence/evidence-id",
        manifest=manifest,
    )

    status = emit_evidence_create(
        argparse.Namespace(json_output=True),
        EvidenceCreateActionResult(record=record),
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "evidence.create"
    assert payload["result"]["schema"] == "cospaces.evidence/v1"
    assert payload["result"]["manifest"]["items"][0]["stored_path"] == "files/0000"


def test_evidence_validation_json_uses_result_envelope(capsys) -> None:
    record = EvidenceValidationRecord(
        bundle_path="bundle",
        evidence_id="evidence-id",
        valid=True,
        checked_files=2,
    )

    status = emit_evidence_validation(
        argparse.Namespace(json_output=True),
        EvidenceValidationActionResult(record=record),
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["operation"] == "evidence.validate"
    assert payload["result"]["schema"] == "cospaces.evidence-validation/v1"
    assert payload["result"]["valid"] is True
