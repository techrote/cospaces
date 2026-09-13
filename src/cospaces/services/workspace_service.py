"""Workspace service module."""

from dataclasses import dataclass

from cospaces.domain.contracts import DomainFailure
from cospaces.domain.workspace import WorkspaceIdentity


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
