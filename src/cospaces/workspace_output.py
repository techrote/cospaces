"""Workspace output module."""

import argparse
import json
import sys

from cospaces.domain.results import failure_result, success_result
from cospaces.services.workspace_service import WorkspaceActionResult


def operation_name(namespace: argparse.Namespace) -> str:
    return f"workspace.{namespace.workspace_operation}"


def emit_failure(namespace: argparse.Namespace, result: WorkspaceActionResult) -> int:
    failure = result.failure
    assert failure is not None
    if namespace.json_output:
        print(failure_result(operation_name(namespace), failure).to_json())
    else:
        print(failure.message, file=sys.stderr)
    return int(failure.exit_status)


def emit_success(namespace: argparse.Namespace, result: WorkspaceActionResult) -> int:
    operation = operation_name(namespace)
    if namespace.workspace_operation == "list":
        payload = [item.to_dict() for item in result.workspaces]
        if namespace.json_output:
            print(
                success_result(
                    operation,
                    result={"count": len(payload), "workspaces": payload},
                ).to_json()
            )
        else:
            for item in result.workspaces:
                print(
                    "\t".join(
                        (
                            item.name,
                            item.repository or "?",
                            item.ref or "?",
                            item.state,
                        )
                    )
                )
        return 0

    workspace = result.workspace
    assert workspace is not None
    details: dict[str, object] = {}
    if result.created:
        details["created"] = True
    if result.stopped is not None:
        details["stopped"] = result.stopped
    if namespace.json_output:
        print(
            success_result(
                operation,
                workspace=workspace.to_dict(),
                result=details,
            ).to_json()
        )
    else:
        print(json.dumps(workspace.to_dict(), sort_keys=True))
    return 0
