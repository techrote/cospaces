import json

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.services.workspace_service import WorkspaceService


class FakeGitHub(GitHubCliAdapter):
    def __init__(self, responses: list[CommandResult | BaseException]) -> None:
        self.responses = responses

    def capture(self, arguments: tuple[str, ...]) -> CommandResult:
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def command_result(stdout: object, *, returncode: int = 0, stderr: str = "") -> CommandResult:
    text = stdout if isinstance(stdout, str) else json.dumps(stdout)
    return CommandResult(argv=("gh",), returncode=returncode, stdout=text, stderr=stderr)


def test_malformed_json_is_infrastructure_failure() -> None:
    service = WorkspaceService(FakeGitHub([command_result("not-json")]))

    listed = service.list("owner/repo")

    assert not listed.ok
    assert listed.failure is not None
    assert listed.failure.code == "invalid_github_response"
    assert int(listed.failure.exit_status) == 3


def test_missing_github_cli_is_infrastructure_failure() -> None:
    service = WorkspaceService(FakeGitHub([FileNotFoundError("gh")]))

    listed = service.list("owner/repo")

    assert not listed.ok
    assert listed.failure is not None
    assert listed.failure.code == "github_cli_unavailable"


def test_github_auth_failure_is_distinct() -> None:
    service = WorkspaceService(
        FakeGitHub([command_result("", returncode=4, stderr="authentication required")])
    )

    listed = service.list("owner/repo")

    assert not listed.ok
    assert listed.failure is not None
    assert listed.failure.code == "github_auth_unavailable"


def test_explicit_missing_codespace_is_selection_failure() -> None:
    service = WorkspaceService(
        FakeGitHub([command_result("", returncode=1, stderr="codespace not found")])
    )

    described = service.describe("missing")

    assert not described.ok
    assert described.failure is not None
    assert described.failure.code == "workspace_not_found"
    assert int(described.failure.exit_status) == 4


def test_malformed_workspace_item_is_rejected() -> None:
    service = WorkspaceService(FakeGitHub([command_result([{"state": "Available"}])]))

    listed = service.list("owner/repo")

    assert not listed.ok
    assert listed.failure is not None
    assert listed.failure.code == "invalid_github_response"
