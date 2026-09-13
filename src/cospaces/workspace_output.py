"""Workspace output module."""

import argparse
import sys

from cospaces.domain.results import failure_result
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
