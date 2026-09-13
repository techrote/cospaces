"""Output rendering for verification operations."""

import argparse
import sys

from cospaces.domain.results import ResultEnvelope, utc_now
from cospaces.services.verification_service import VerificationActionResult


def emit_verification_result(
    namespace: argparse.Namespace,
    result: VerificationActionResult,
) -> int:
    now = utc_now()
    record = result.record
    envelope = ResultEnvelope(
        operation="verify",
        ok=result.ok,
        started_at=record.started_at if record is not None else now,
        finished_at=record.finished_at if record is not None else now,
        workspace=(
            dict(record.workspace)
            if record is not None and record.workspace is not None
            else None
        ),
        result=record.to_dict() if record is not None else None,
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    elif record is not None:
        for check in record.checks:
            status = "PASS" if check.passed else ("TIMEOUT" if check.timed_out else "FAIL")
            requirement = "required" if check.required else "optional"
            print(f"{status}\t{requirement}\t{check.name}\t{check.run_id}")
        summary = "passed" if record.passed else "failed"
        completeness = "complete" if record.complete else "incomplete"
        print(
            f"verification {record.verification_id}: {summary} ({completeness})",
            file=sys.stderr,
        )
        if result.failure is not None:
            print(result.failure.message, file=sys.stderr)
    elif result.failure is not None:
        print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0
