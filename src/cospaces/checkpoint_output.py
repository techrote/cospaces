"""Output rendering for checkpoint operations."""

import argparse
import json
import sys
from pathlib import Path

from cospaces.domain.results import ResultEnvelope, utc_now
from cospaces.services.checkpoint_service import CheckpointActionResult


def _display_path(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _result_payload(
    operation: str,
    result: CheckpointActionResult,
    root: Path,
) -> dict[str, object]:
    if operation == "checkpoint.list":
        entries = [entry.to_dict(root) for entry in result.entries]
        return {"count": len(entries), "checkpoints": entries}
    return {
        "checkpoint": result.document.to_dict() if result.document is not None else None,
        "path": _display_path(result.path, root),
        "previous_path": _display_path(result.previous_path, root),
        "source_control_action": "none",
        "live_checked": result.live_checked,
        "mismatches": [mismatch.to_dict() for mismatch in result.mismatches],
    }


def emit_checkpoint_result(
    namespace: argparse.Namespace,
    result: CheckpointActionResult,
    root: Path,
) -> int:
    operation = f"checkpoint.{namespace.checkpoint_operation}"
    now = utc_now()
    payload = _result_payload(operation, result, root)
    envelope = ResultEnvelope(
        operation=operation,
        ok=result.ok,
        started_at=now,
        finished_at=now,
        result=payload,
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    elif operation == "checkpoint.list":
        for entry in result.entries:
            print(
                "\t".join(
                    (
                        entry.task_id,
                        entry.status,
                        entry.updated_at or "?",
                        entry.error_code or "-",
                    )
                )
            )
    else:
        if result.document is not None:
            print(json.dumps(result.document.to_dict(), indent=2, sort_keys=True))
        for mismatch in result.mismatches:
            message = (
                f"mismatch: {mismatch.field}: expected={mismatch.expected!r} "
                f"actual={mismatch.actual!r}"
            )
            print(message, file=sys.stderr)
        if result.failure is not None:
            print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0
