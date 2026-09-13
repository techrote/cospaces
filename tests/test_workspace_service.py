import json

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.services.workspace_service import WorkspaceService


class FakeGitHub(GitHubCliAdapter):
    def __init__(self, responses: list[CommandResult | BaseException]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def capture(self, arguments: tuple[str, ...]) -> CommandResult:
        self.calls.append(arguments)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def result(stdout: object, *, returncode: int = 0, stderr: str = "") -> CommandResult:
    text = stdout if isinstance(stdout, str) else json.dumps(stdout)
    return CommandResult(argv=("gh",), returncode=returncode, stdout=text, stderr=stderr)


def workspace(name: str, *, ref: str = "main", repo: str = "owner/repo") -> dict[str, object]:
    return {
        "name": name,
        "repository": repo,
        "gitStatus": {"ref": ref},
        "state": "Available",
        "displayName": name,
        "machineName": "standard",
    }


def test_list_uses_repository_filter_and_machine_json() -> None:
    github = FakeGitHub([result([workspace("one")])])
    service = WorkspaceService(github)

    listed = service.list("owner/repo")

    assert listed.ok
    assert [item.name for item in listed.workspaces] == ["one"]
    assert github.calls == [
        (
            "codespace",
            "list",
            "--repo",
            "owner/repo",
            "--limit",
            "1000",
            "--json",
            "name,repository,gitStatus,state,displayName,machineName",
        )
    ]


def test_resolve_filters_exact_ref() -> None:
    github = FakeGitHub(
        [result([workspace("main-space"), workspace("feature-space", ref="feature")])]
    )
    service = WorkspaceService(github)

    resolved = service.resolve("owner/repo", ref="feature")

    assert resolved.ok
    assert resolved.workspace is not None
    assert resolved.workspace.name == "feature-space"


def test_resolve_zero_candidates_is_not_found() -> None:
    service = WorkspaceService(FakeGitHub([result([])]))

    resolved = service.resolve("owner/repo")

    assert not resolved.ok
    assert resolved.failure is not None
    assert resolved.failure.code == "workspace_not_found"
    assert int(resolved.failure.exit_status) == 4
