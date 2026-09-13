from uuid import UUID

from cospaces.adapters.process import CommandResult
from cospaces.domain.run import RunRequest
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.run_service import RunService
from cospaces.services.run_transport import TransportOutcome
from cospaces.services.workspace_service import WorkspaceActionResult


def identity(name: str = "space-one") -> WorkspaceIdentity:
    return WorkspaceIdentity(
        name=name,
        repository="owner/repo",
        ref="main",
        state="available",
        display_name=name,
        machine="standard",
    )


class FakeWorkspace:
    def __init__(self, outcome: WorkspaceActionResult) -> None:
        self.outcome = outcome
        self.calls: list[tuple[object, ...]] = []

    def describe(self, name: str) -> WorkspaceActionResult:
        self.calls.append(("describe", name))
        return self.outcome

    def resolve(
        self,
        repository: str,
        *,
        ref: str | None = None,
        name: str | None = None,
    ) -> WorkspaceActionResult:
        self.calls.append(("resolve", repository, ref, name))
        return self.outcome


class FakeTransport:
    def __init__(self, outcome: TransportOutcome) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, tuple[str, ...], float]] = []

    def execute(
        self,
        codespace: str,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> TransportOutcome:
        self.calls.append((codespace, argv, timeout_seconds))
        return self.outcome


def process_result(
    returncode: int | None,
    *,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
) -> CommandResult:
    return CommandResult(
        argv=("gh",),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


def test_explicit_codespace_is_described_and_success_is_structured() -> None:
    workspace = FakeWorkspace(WorkspaceActionResult(workspace=identity()))
    transport = FakeTransport(TransportOutcome(result=process_result(0, stdout="ok\n")))
    service = RunService(workspace=workspace, transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(
        RunRequest(
            argv=("printf", "%s", "hello"),
            codespace="space-one",
            timeout_seconds=8.0,
            task_id="issue-3",
            correlation_id="chat-1",
        )
    )

    assert outcome.ok
    assert workspace.calls == [("describe", "space-one")]
    assert transport.calls == [("space-one", ("printf", "%s", "hello"), 8.0)]
    assert UUID(outcome.record.run_id)
    assert outcome.record.task_id == "issue-3"
    assert outcome.record.correlation_id == "chat-1"
    assert outcome.record.exit_code == 0
    assert outcome.record.remote_completion == "success"
    assert outcome.record.stdout == "ok\n"
    assert outcome.record.stderr_mixed is True
    assert outcome.record.duration_seconds >= 0


def test_repository_target_delegates_to_t1_resolution() -> None:
    workspace = FakeWorkspace(WorkspaceActionResult(workspace=identity()))
    transport = FakeTransport(TransportOutcome(result=process_result(0)))
    service = RunService(workspace=workspace, transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(
        RunRequest(argv=("true",), repository="owner/repo", ref="main")
    )

    assert outcome.ok
    assert workspace.calls == [("resolve", "owner/repo", "main", None)]


def test_remote_nonzero_is_remote_failure_without_retry() -> None:
    workspace = FakeWorkspace(WorkspaceActionResult(workspace=identity()))
    transport = FakeTransport(
        TransportOutcome(result=process_result(23, stdout="out", stderr="err"))
    )
    service = RunService(workspace=workspace, transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(RunRequest(argv=("false",), codespace="space-one"))

    assert not outcome.ok
    assert outcome.failure is not None
    assert outcome.failure.code == "remote_task_failed"
    assert int(outcome.failure.exit_status) == 5
    assert outcome.record.exit_code == 23
    assert outcome.record.remote_completion == "failed"
    assert len(transport.calls) == 1


def test_timeout_is_remote_failure_and_completion_remains_unknown() -> None:
    workspace = FakeWorkspace(WorkspaceActionResult(workspace=identity()))
    transport = FakeTransport(
        TransportOutcome(
            result=process_result(None, stdout="partial", stderr="diag", timed_out=True)
        )
    )
    service = RunService(workspace=workspace, transport=transport)  # type: ignore[arg-type]

    outcome = service.execute(
        RunRequest(argv=("slow-task",), codespace="space-one", timeout_seconds=1.0)
    )

    assert not outcome.ok
    assert outcome.failure is not None
    assert outcome.failure.code == "remote_timeout"
    assert int(outcome.failure.exit_status) == 5
    assert outcome.record.timed_out is True
    assert outcome.record.remote_completion == "unknown"
    assert outcome.record.stdout == "partial"
