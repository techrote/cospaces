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
