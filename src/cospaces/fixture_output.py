"""Output rendering for T6 fixtures."""

import argparse
import sys

from cospaces.domain.results import ResultEnvelope, utc_now
from cospaces.services.fixture_service import FixtureActionResult


def emit_fixture_result(namespace: argparse.Namespace, result: FixtureActionResult) -> int:
    now = utc_now()
    record = result.record
    envelope = ResultEnvelope(
        operation="fixture",
        ok=result.ok,
        started_at=record.started_at if record is not None else now,
        finished_at=record.finished_at if record is not None else now,
        workspace=record.workspace.to_dict() if record is not None else None,
        result=record.to_dict() if record is not None else None,
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    elif record is not None:
        print(
            f"{record.fixture}\tpassed={str(record.passed).lower()}\t"
            f"complete={str(record.complete).lower()}\t{record.fixture_run_id}"
        )
        for metric, value in sorted(record.metrics.items()):
            print(f"metric\t{metric}\t{value}")
        for assertion in record.assertions:
            print(
                f"assertion\t{assertion.metric}\t{assertion.operator}\t"
                f"passed={str(assertion.passed).lower()}"
            )
    elif result.failure is not None:
        print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0
