import json

from cospaces.cli import build_parser
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.workspace_service import WorkspaceActionResult
from cospaces.workspace_dispatch import run_workspace


def identity(name: str = "one") -> WorkspaceIdentity:
    return WorkspaceIdentity(
        name=name,
        repository="owner/repo",
        ref="main",
        state="available",
        display_name=name,
        machine="standard",
    )


class FakeService:
    def __init__(self, result: WorkspaceActionResult) -> None:
        self.result = result
        self.last_request = None

    def list(self, repository: str) -> WorkspaceActionResult:
        self.last_request = ("list", repository)
        return self.result

    def describe(self, name: str) -> WorkspaceActionResult:
        self.last_request = ("describe", name)
        return self.result

    def ensure(self, repository: str, **kwargs) -> WorkspaceActionResult:
        self.last_request = ("ensure", repository, kwargs)
        return self.result

    def create(self, request) -> WorkspaceActionResult:
        self.last_request = ("create", request)
        return self.result

    def stop(self, name: str) -> WorkspaceActionResult:
        self.last_request = ("stop", name)
        return self.result


def test_workspace_list_json_is_one_parseable_document(capsys) -> None:
    namespace = build_parser().parse_args(
        ["workspace", "list", "--repo", "owner/repo", "--json"]
    )
    service = FakeService(WorkspaceActionResult(workspaces=(identity(),)))

    status = run_workspace(namespace, service)  # type: ignore[arg-type]

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 0
    assert captured.err == ""
    assert payload["operation"] == "workspace.list"
    assert payload["ok"] is True
    assert payload["result"]["count"] == 1
    assert payload["result"]["workspaces"][0]["name"] == "one"


def test_workspace_selection_failure_has_selection_exit_code(capsys) -> None:
    namespace = build_parser().parse_args(
        ["workspace", "ensure", "--repo", "owner/repo", "--json"]
    )
    failure = DomainFailure(
        code="ambiguous_workspace",
        kind=FailureKind.SELECTION,
        message="ambiguous",
    )
    service = FakeService(WorkspaceActionResult(failure=failure))

    status = run_workspace(namespace, service)  # type: ignore[arg-type]

    payload = json.loads(capsys.readouterr().out)
    assert status == 4
    assert payload["ok"] is False
    assert payload["error"]["code"] == "ambiguous_workspace"


def test_workspace_create_parser_passes_creation_options(capsys) -> None:
    namespace = build_parser().parse_args(
        [
            "workspace",
            "create",
            "--repo",
            "owner/repo",
            "--branch",
            "feature",
            "--machine",
            "large",
            "--json",
        ]
    )
    service = FakeService(WorkspaceActionResult(workspace=identity(), created=True))

    status = run_workspace(namespace, service)  # type: ignore[arg-type]

    assert status == 0
    assert service.last_request is not None
    _, request = service.last_request
    assert request.repository == "owner/repo"
    assert request.branch == "feature"
    assert request.machine == "large"
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["created"] is True
