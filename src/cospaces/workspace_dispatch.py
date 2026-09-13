"""Workspace command dispatch module."""

import argparse

from cospaces.services.workspace_lifecycle import WorkspaceLifecycleService
from cospaces.services.workspace_service import CreateWorkspaceRequest
from cospaces.workspace_output import emit_failure, emit_success


def creation_request(
    namespace: argparse.Namespace,
    *,
    branch: str | None,
) -> CreateWorkspaceRequest:
    return CreateWorkspaceRequest(
        repository=str(namespace.repo),
        branch=branch,
        devcontainer_path=namespace.devcontainer_path,
        display_name=namespace.display_name,
        idle_timeout=namespace.idle_timeout,
        machine=namespace.machine,
        location=namespace.location,
        retention_period=namespace.retention_period,
    )


def run_workspace(
    namespace: argparse.Namespace,
    service: WorkspaceLifecycleService | None = None,
) -> int:
    active = service or WorkspaceLifecycleService()
    operation = str(namespace.workspace_operation)
    if operation == "list":
        result = active.list(str(namespace.repo))
    elif operation == "describe":
        result = active.describe(str(namespace.codespace))
    elif operation == "ensure":
        result = active.ensure(
            str(namespace.repo),
            ref=namespace.ref,
            name=namespace.codespace,
            allow_create=bool(namespace.create),
            create_request=creation_request(namespace, branch=namespace.ref),
        )
    elif operation == "create":
        result = active.create(creation_request(namespace, branch=namespace.branch))
    elif operation == "stop":
        result = active.stop(str(namespace.codespace))
    else:
        raise AssertionError(f"Unsupported workspace operation: {operation}")

    if not result.ok:
        return emit_failure(namespace, result)
    return emit_success(namespace, result)
