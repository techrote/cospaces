"""Checkpoint command dispatch."""

import argparse
from pathlib import Path

from cospaces.checkpoint_output import emit_checkpoint_result
from cospaces.services.checkpoint_service import CheckpointSaveRequest, CheckpointService


def run_checkpoint(
    namespace: argparse.Namespace,
    service: CheckpointService | None = None,
) -> int:
    root = service.root if service is not None else Path(str(namespace.root)).resolve()
    active = service or CheckpointService(root)
    operation = str(namespace.checkpoint_operation)

    if operation == "save":
        completed = tuple(namespace.completed) if namespace.completed is not None else None
        record_paths = tuple(namespace.record_path) if namespace.record_path is not None else None
        result = active.save(
            CheckpointSaveRequest(
                task_id=str(namespace.task),
                repository=namespace.repo,
                ref=namespace.ref,
                head=namespace.head,
                codespace=namespace.codespace,
                capture_git=not bool(namespace.no_git),
                completed=completed,
                current=namespace.current,
                next_step=namespace.next_step,
                last_run_id=namespace.last_run_id,
                last_verification_id=namespace.last_verification_id,
                record_paths=record_paths,
                notes=namespace.notes,
            )
        )
    elif operation == "show":
        result = active.show(str(namespace.task))
    elif operation == "list":
        result = active.list()
    elif operation == "validate":
        result = active.validate(
            str(namespace.task),
            live=bool(namespace.live),
            codespace=namespace.codespace,
        )
    else:
        raise AssertionError(f"Unsupported checkpoint operation: {operation}")
    return emit_checkpoint_result(namespace, result, root)
