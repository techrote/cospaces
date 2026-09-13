"""Output rendering for structured remote runs."""

import argparse
import sys

from cospaces.domain.results import ResultEnvelope
from cospaces.services.run_service import RunActionResult


def emit_run_result(namespace: argparse.Namespace, result: RunActionResult) -> int:
    record = result.record
    workspace = result.workspace.to_dict() if result.workspace is not None else None
    envelope = ResultEnvelope(
        operation="run",
        ok=result.ok,
        started_at=record.started_at,
        finished_at=record.finished_at,
        workspace=workspace,
        result=record.to_dict(),
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    else:
        if record.stdout:
            print(record.stdout, end="")
        if record.stderr:
            print(record.stderr, end="", file=sys.stderr)
        if result.failure is not None:
            print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0
