"""Workspace service module."""

import json
from dataclasses import dataclass
from typing import Any

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.workspace import WorkspaceIdentity

_JSON_FIELDS = "name,repository,gitStatus,state,displayName,machineName"


@dataclass(frozen=True)
class CreateWorkspaceRequest:
    repository: str
    branch: str | None = None
    devcontainer_path: str | None = None
    display_name: str | None = None
    idle_timeout: str | None = None
    machine: str | None = None
    location: str | None = None
    retention_period: str | None = None


@dataclass(frozen=True)
class WorkspaceActionResult:
    workspace: WorkspaceIdentity | None = None
    workspaces: tuple[WorkspaceIdentity, ...] = ()
    created: bool = False
    stopped: bool | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


class WorkspaceService:
    def __init__(self, github: GitHubCliAdapter | None = None) -> None:
        self._github = github or GitHubCliAdapter()

    def _failure(
        self,
        code: str,
        message: str,
        *,
        kind: FailureKind = FailureKind.INFRASTRUCTURE,
        retryable: bool = False,
    ) -> WorkspaceActionResult:
        return WorkspaceActionResult(
            failure=DomainFailure(
                code=code,
                kind=kind,
                message=message,
                retryable=retryable,
            )
        )

    def _capture(
        self,
        arguments: tuple[str, ...],
    ) -> tuple[CommandResult | None, DomainFailure | None]:
        try:
            result = self._github.capture(arguments)
        except (FileNotFoundError, OSError):
            return None, DomainFailure(
                code="github_cli_unavailable",
                kind=FailureKind.INFRASTRUCTURE,
                message="GitHub CLI is unavailable",
            )
        if result.returncode == 0:
            return result, None
        stderr = result.stderr.casefold()
        if result.returncode == 4 or "authentication" in stderr or "not logged" in stderr:
            return None, DomainFailure(
                code="github_auth_unavailable",
                kind=FailureKind.INFRASTRUCTURE,
                message="GitHub CLI authentication is unavailable",
            )
        return None, DomainFailure(
            code="codespaces_control_plane_error",
            kind=FailureKind.INFRASTRUCTURE,
            message="GitHub Codespaces control-plane operation failed",
            retryable=True,
        )

    def _decode(self, result: CommandResult) -> Any | None:
        try:
            return json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            return None
