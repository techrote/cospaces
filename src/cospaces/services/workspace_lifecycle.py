"""Workspace mutation and ensure operations."""

from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.workspace_service import (
    CreateWorkspaceRequest,
    WorkspaceActionResult,
    WorkspaceService,
)


class WorkspaceLifecycleService(WorkspaceService):
    def create(self, request: CreateWorkspaceRequest) -> WorkspaceActionResult:
        arguments: list[str] = [
            "codespace",
            "create",
            "--repo",
            request.repository,
            "--default-permissions",
        ]
        options = (
            ("--branch", request.branch),
            ("--devcontainer-path", request.devcontainer_path),
            ("--display-name", request.display_name),
            ("--idle-timeout", request.idle_timeout),
            ("--machine", request.machine),
            ("--location", request.location),
            ("--retention-period", request.retention_period),
        )
        for flag, value in options:
            if value is not None:
                arguments.extend((flag, value))

        result, failure = self._capture(tuple(arguments))
        if failure is not None:
            return WorkspaceActionResult(failure=failure)
        assert result is not None
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(names) != 1:
            return self._failure(
                "invalid_github_response",
                "GitHub CLI did not return exactly one created Codespace name",
            )

        name = names[0]
        described = self.describe(name)
        if described.ok:
            return WorkspaceActionResult(workspace=described.workspace, created=True)
        return WorkspaceActionResult(
            workspace=WorkspaceIdentity(
                name=name,
                repository=request.repository,
                ref=request.branch,
                state="unknown",
                display_name=request.display_name,
                machine=request.machine,
            ),
            created=True,
        )

    def ensure(
        self,
        repository: str,
        *,
        ref: str | None = None,
        name: str | None = None,
        allow_create: bool = False,
        create_request: CreateWorkspaceRequest | None = None,
    ) -> WorkspaceActionResult:
        resolved = self.resolve(repository, ref=ref, name=name)
        if resolved.ok:
            return resolved
        failure = resolved.failure
        assert failure is not None
        if failure.code != "workspace_not_found" or not allow_create or name is not None:
            return resolved
        request = create_request or CreateWorkspaceRequest(
            repository=repository,
            branch=ref,
        )
        return self.create(request)

    def stop(self, name: str) -> WorkspaceActionResult:
        described = self.describe(name)
        if not described.ok:
            return described
        workspace = described.workspace
        assert workspace is not None
        if workspace.state == "shutdown":
            return WorkspaceActionResult(workspace=workspace, stopped=False)

        _, failure = self._capture(("codespace", "stop", "--codespace", name))
        if failure is not None:
            return WorkspaceActionResult(failure=failure)
        refreshed = self.describe(name)
        if refreshed.ok:
            return WorkspaceActionResult(workspace=refreshed.workspace, stopped=True)
        return WorkspaceActionResult(
            workspace=WorkspaceIdentity(
                name=workspace.name,
                repository=workspace.repository,
                ref=workspace.ref,
                state="unknown",
                display_name=workspace.display_name,
                machine=workspace.machine,
            ),
            stopped=True,
        )
