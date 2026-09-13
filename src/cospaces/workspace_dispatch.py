"""Workspace command dispatch module."""

import argparse

from cospaces.services.workspace_service import CreateWorkspaceRequest


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
