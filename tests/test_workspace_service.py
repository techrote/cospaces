import json

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.services.workspace_service import WorkspaceService


class FakeGitHub(GitHubCliAdapter):
    def __init__(self, responses: list[CommandResult | BaseException]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []
        self.timeouts: list[float | None] = []

    def capture(
        self,
        arguments: tuple[str, ...],
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        self.calls.append(arguments)
        self.timeouts.append(timeout_seconds)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def result(
    stdout: object,
    *,
    returncode: int = 0,
    stderr: str = "",
    timed_out: bool = False,
) -> CommandResult:
    text = stdout if isinstance(stdout, str) else json.dumps(stdout)
    return CommandResult(
        argv=("gh",),
        returncode=returncode,
        stdout=text,
        stderr=stderr,
        timed_out=timed_out,
    )


def workspace(name: str, *, ref: str = "main", repo: str = "owner/repo") -> dict[str, object]:
    return {
        "name": name,
        "repository": repo,
        "gitStatus": {"ref": ref},
        "state": "Available",
        "displayName": name,
        "machineName": "standard",
    }


def test_list_uses_repository_filter_and_bounded_machine_json() -> None:
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
    assert github.timeouts == [120.0]


def test_control_plane_timeout_is_retryable_infrastructure_failure() -> None:
    service = WorkspaceService(FakeGitHub([result("", returncode=0, timed_out=True)]))

    listed = service.list("owner/repo")

    assert not listed.ok
    assert listed.failure is not None
    assert listed.failure.code == "codespaces_control_plane_timeout"
    assert listed.failure.retryable is True
    assert int(listed.failure.exit_status) == 3


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


def test_resolve_unknown_candidate_ref_is_not_guessed() -> None:
    unknown = workspace("one")
    unknown["gitStatus"] = {}
    service = WorkspaceService(FakeGitHub([result([unknown])]))

    resolved = service.resolve("owner/repo", ref="feature")

    assert not resolved.ok
    assert resolved.failure is not None
    assert resolved.failure.code == "workspace_ref_unknown"


def test_known_match_plus_unknown_ref_is_not_silently_selected() -> None:
    unknown = workspace("unknown")
    unknown["gitStatus"] = {}
    service = WorkspaceService(
        FakeGitHub([result([workspace("known", ref="feature"), unknown])])
    )

    resolved = service.resolve("owner/repo", ref="feature")

    assert not resolved.ok
    assert resolved.failure is not None
    assert resolved.failure.code == "workspace_ref_unknown"


def test_resolve_multiple_candidates_is_ambiguous() -> None:
    service = WorkspaceService(FakeGitHub([result([workspace("one"), workspace("two")])]))

    resolved = service.resolve("owner/repo")

    assert not resolved.ok
    assert resolved.failure is not None
    assert resolved.failure.code == "ambiguous_workspace"


def test_explicit_name_is_described_and_repository_mismatch_is_rejected() -> None:
    github = FakeGitHub([result(workspace("chosen", repo="other/repo"))])
    service = WorkspaceService(github)

    resolved = service.resolve("owner/repo", name="chosen")

    assert not resolved.ok
    assert resolved.failure is not None
    assert resolved.failure.code == "workspace_repository_mismatch"
    assert github.calls[0][:4] == ("codespace", "view", "--codespace", "chosen")


def test_explicit_name_ref_mismatch_is_rejected() -> None:
    service = WorkspaceService(FakeGitHub([result(workspace("chosen", ref="other"))]))

    resolved = service.resolve("owner/repo", ref="wanted", name="chosen")

    assert not resolved.ok
    assert resolved.failure is not None
    assert resolved.failure.code == "workspace_ref_mismatch"
