import json

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.services.workspace_lifecycle import WorkspaceLifecycleService
from cospaces.services.workspace_service import CreateWorkspaceRequest


class FakeGitHub(GitHubCliAdapter):
    def __init__(self, responses: list[CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def capture(self, arguments: tuple[str, ...]) -> CommandResult:
        self.calls.append(arguments)
        return self.responses.pop(0)


def result(stdout: object = "", *, returncode: int = 0, stderr: str = "") -> CommandResult:
    text = stdout if isinstance(stdout, str) else json.dumps(stdout)
    return CommandResult(argv=("gh",), returncode=returncode, stdout=text, stderr=stderr)


def workspace(name: str, *, state: str = "Available", ref: str = "main") -> dict[str, object]:
    return {
        "name": name,
        "repository": "owner/repo",
        "gitStatus": {"ref": ref},
        "state": state,
        "displayName": name,
        "machineName": "standard",
    }


def test_create_builds_explicit_noninteractive_options() -> None:
    github = FakeGitHub([result("new-space\n"), result(workspace("new-space", ref="feature"))])
    service = WorkspaceLifecycleService(github)
    request = CreateWorkspaceRequest(
        repository="owner/repo",
        branch="feature",
        devcontainer_path=".devcontainer/devcontainer.json",
        display_name="agent",
        idle_timeout="1h",
        machine="premiumLinux",
        location="WestEurope",
        retention_period="72h",
    )

    created = service.create(request)

    assert created.ok
    assert created.created is True
    assert github.calls[0] == (
        "codespace",
        "create",
        "--repo",
        "owner/repo",
        "--default-permissions",
        "--branch",
        "feature",
        "--devcontainer-path",
        ".devcontainer/devcontainer.json",
        "--display-name",
        "agent",
        "--idle-timeout",
        "1h",
        "--machine",
        "premiumLinux",
        "--location",
        "WestEurope",
        "--retention-period",
        "72h",
    )


def test_ensure_does_not_create_without_explicit_permission() -> None:
    github = FakeGitHub([result([])])
    service = WorkspaceLifecycleService(github)

    ensured = service.ensure("owner/repo", ref="feature")

    assert not ensured.ok
    assert ensured.failure is not None
    assert ensured.failure.code == "workspace_not_found"
    assert len(github.calls) == 1


def test_ensure_create_uses_requested_ref_as_branch() -> None:
    github = FakeGitHub(
        [
            result([]),
            result("new-space\n"),
            result(workspace("new-space", ref="feature")),
        ]
    )
    service = WorkspaceLifecycleService(github)

    ensured = service.ensure("owner/repo", ref="feature", allow_create=True)

    assert ensured.ok
    assert ensured.created is True
    assert "--branch" in github.calls[1]
    assert "feature" in github.calls[1]


def test_stop_is_noop_for_shutdown_workspace() -> None:
    github = FakeGitHub([result(workspace("one", state="Shutdown"))])
    service = WorkspaceLifecycleService(github)

    stopped = service.stop("one")

    assert stopped.ok
    assert stopped.stopped is False
    assert len(github.calls) == 1


def test_stop_refreshes_identity_after_success() -> None:
    github = FakeGitHub(
        [
            result(workspace("one")),
            result(),
            result(workspace("one", state="Shutdown")),
        ]
    )
    service = WorkspaceLifecycleService(github)

    stopped = service.stop("one")

    assert stopped.ok
    assert stopped.stopped is True
    assert stopped.workspace is not None
    assert stopped.workspace.state == "shutdown"
    assert github.calls[1] == ("codespace", "stop", "--codespace", "one")


def test_stop_control_plane_failure_is_reported() -> None:
    github = FakeGitHub(
        [
            result(workspace("one")),
            result(returncode=1, stderr="service unavailable"),
        ]
    )
    service = WorkspaceLifecycleService(github)

    stopped = service.stop("one")

    assert not stopped.ok
    assert stopped.failure is not None
    assert stopped.failure.code == "codespaces_control_plane_error"
