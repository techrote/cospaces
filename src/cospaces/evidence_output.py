"""Output rendering for T7 evidence operations."""

import argparse
import sys

from cospaces.domain.results import ResultEnvelope, utc_now
from cospaces.services.evidence_service import (
    EvidenceCreateActionResult,
    EvidenceValidationActionResult,
)


def emit_evidence_create(
    namespace: argparse.Namespace,
    result: EvidenceCreateActionResult,
) -> int:
    now = utc_now()
    envelope = ResultEnvelope(
        operation="evidence.create",
        ok=result.ok,
        started_at=now,
        finished_at=now,
        result=result.record.to_dict() if result.record is not None else None,
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    elif result.record is not None:
        print(f"{result.record.evidence_id}\t{result.record.bundle_path}")
    elif result.failure is not None:
        print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0


def emit_evidence_validation(
    namespace: argparse.Namespace,
    result: EvidenceValidationActionResult,
) -> int:
    now = utc_now()
    envelope = ResultEnvelope(
        operation="evidence.validate",
        ok=result.ok,
        started_at=now,
        finished_at=now,
        result=result.record.to_dict() if result.record is not None else None,
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    elif result.record is not None:
        print(
            f"valid={str(result.record.valid).lower()}\t"
            f"files={result.record.checked_files}\t{result.record.bundle_path}"
        )
    elif result.failure is not None:
        print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0
