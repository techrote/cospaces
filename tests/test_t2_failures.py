from cospaces.adapters.process import CommandResult
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRequest
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.run_service import RunService
from cospaces.services.run_transport import TransportOutcome
from cospaces.services.workspace_service import WorkspaceActionResult


class FakeWorkspace:
    def describe(self, name: str) -> WorkspaceActionResult:
        return WorkspaceActionResult(
            workspace=WorkspaceIdentity(
                name=name,
                repository="owner/repo",
                ref="main",
                state="available",
                display_name=name,
                machine="standard",
            )
        )

    def resolve(self, repository: str, *, ref=None, name=None) -> WorkspaceActionResult:
        return self.describe(name or "space-one")


class FakeTransport:
    def __init__(self, outcome: TransportOutcome) -> None:
        self.outcome = outcome
        self.calls = 0

    def execute(self, codespace: str, argv: tuple[str, ...], *, timeout_seconds: float):
        self.calls += 1
        return self.outcome


def test_status_255_is_transport_failure() -> None:
    result = CommandResult(
        argv=("gh",),
        returncode=255,
        stdout="",
        stderr="ssh diagnostic",
    )
    transport = FakeTransport(TransportOutcome(result=result))
    service = RunService(workspace=FakeWorkspace(), transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(RunRequest(argv=("tool",), codespace="space-one"))

    assert not outcome.ok
    assert outcome.failure is not None
    assert outcome.failure.code == "transport_failure"
    assert int(outcome.failure.exit_status) == 3
    assert outcome.record.remote_completion == "unknown"
    assert transport.calls == 1


def test_transport_preflight_failure_is_distinct() -> None:
    failure = DomainFailure(
        code="unsafe_github_cli_version",
        kind=FailureKind.INFRASTRUCTURE,
        message="upgrade gh",
    )
    transport = FakeTransport(TransportOutcome(failure=failure))
    service = RunService(workspace=FakeWorkspace(), transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(RunRequest(argv=("tool",), codespace="space-one"))

    assert not outcome.ok
    assert outcome.failure == failure
    assert outcome.record.remote_completion == "not_started"


def test_missing_target_is_usage_failure_without_transport() -> None:
    transport = FakeTransport(
        TransportOutcome(
            result=CommandResult(argv=("gh",), returncode=0, stdout="", stderr="")
        )
    )
    service = RunService(workspace=FakeWorkspace(), transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(RunRequest(argv=("tool",)))

    assert not outcome.ok
    assert outcome.failure is not None
    assert outcome.failure.code == "workspace_target_required"
    assert int(outcome.failure.exit_status) == 2
    assert transport.calls == 0
