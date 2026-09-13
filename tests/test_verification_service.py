from pathlib import Path
from uuid import UUID

from cospaces.domain.checkpoint import WorkingTreeState
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbeResult
from cospaces.services.run_service import RunActionResult
from cospaces.services.verification_service import VerificationRequest, VerificationService


class FakeProbe:
    def capture(self) -> RepositoryProbeResult:
        return RepositoryProbeResult(
            context=RepositoryContext(
                repository="owner/repo",
                ref="main",
                head="abc123",
                working_tree=WorkingTreeState(
                    dirty=False,
                    summary="modified=0;added=0;deleted=0;renamed=0;untracked=0;conflicted=0",
                ),
            )
        )


class FakeRunService:
    def __init__(self, outcomes: list[RunActionResult]) -> None:
        self.outcomes = outcomes
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.outcomes.pop(0)


def workspace() -> WorkspaceIdentity:
    return WorkspaceIdentity(
        name="space-one",
        repository="owner/repo",
        ref="main",
        state="available",
        display_name="space-one",
        machine="standard",
    )


def outcome(
    run_id: str,
    *,
    exit_code: int | None = 0,
    timed_out: bool = False,
    failure: DomainFailure | None = None,
) -> RunActionResult:
    return RunActionResult(
        workspace=workspace(),
        record=RunRecord(
            run_id=run_id,
            argv=("remote",),
            task_id="issue-5",
            correlation_id="verification",
            timeout_seconds=60.0,
            exit_code=exit_code,
            timed_out=timed_out,
            remote_completion=(
                "unknown" if timed_out else ("success" if failure is None else "failed")
            ),
            transport="gh-codespace-ssh",
            stdout="",
            stderr="",
            stderr_mixed=True,
            duration_seconds=0.125,
            started_at="2026-09-13T20:00:00Z",
            finished_at="2026-09-13T20:00:00.125000Z",
        ),
        failure=failure,
    )


def write_plan(root: Path, *, optional_first: bool = False) -> None:
    required = "false" if optional_first else "true"
    (root / ".cospaces.toml").write_text(
        f"""
[cospaces]
schema_version = 1

[verify.default]
[[verify.default.checks]]
name = "first"
command = ["first-command"]
timeout_seconds = 30
required = {required}

[[verify.default.checks]]
name = "second"
command = ["second-command"]
timeout_seconds = 40
required = true
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_checks_run_sequentially_and_lock_first_workspace(tmp_path: Path) -> None:
    write_plan(tmp_path)
    runner = FakeRunService([outcome("run-1"), outcome("run-2")])
    service = VerificationService(
        tmp_path,
        run_service=runner,  # type: ignore[arg-type]
        probe=FakeProbe(),  # type: ignore[arg-type]
    )

    result = service.verify(
        VerificationRequest(
            repository="owner/repo",
            ref="main",
            task_id="issue-5",
            correlation_id="chat-1",
        )
    )

    assert result.ok
    assert result.record is not None
    assert result.record.complete is True
    assert result.record.passed is True
    assert [check.name for check in result.record.checks] == ["first", "second"]
    assert [request.argv[-1] for request in runner.requests] == [
        "first-command",
        "second-command",
    ]
    assert runner.requests[0].codespace is None
    assert runner.requests[1].codespace == "space-one"
    assert all(
        request.correlation_id == result.record.verification_id
        for request in runner.requests
    )
    assert UUID(result.record.verification_id)
    assert result.record.repository == "owner/repo"
    assert result.record.ref == "main"
    assert result.record.head == "abc123"
    assert result.record.workspace is not None
    assert result.record.workspace["name"] == "space-one"


def test_required_failure_sets_verification_exit_and_continues(tmp_path: Path) -> None:
    write_plan(tmp_path)
    failure = DomainFailure(
        code="remote_task_failed",
        kind=FailureKind.REMOTE,
        message="remote failed",
    )
    runner = FakeRunService(
        [outcome("run-1", exit_code=23, failure=failure), outcome("run-2")]
    )
    service = VerificationService(tmp_path, run_service=runner)  # type: ignore[arg-type]

    result = service.verify(VerificationRequest(codespace="space-one"))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "verification_failed"
    assert int(result.failure.exit_status) == 7
    assert result.record is not None
    assert result.record.complete is True
    assert result.record.passed is False
    assert [check.passed for check in result.record.checks] == [False, True]
    assert len(runner.requests) == 2


def test_optional_failure_remains_visible_but_aggregate_passes(tmp_path: Path) -> None:
    write_plan(tmp_path, optional_first=True)
    failure = DomainFailure(
        code="remote_task_failed",
        kind=FailureKind.REMOTE,
        message="optional failed",
    )
    runner = FakeRunService(
        [outcome("run-1", exit_code=9, failure=failure), outcome("run-2")]
    )
    service = VerificationService(tmp_path, run_service=runner)  # type: ignore[arg-type]

    result = service.verify(VerificationRequest(codespace="space-one"))

    assert result.ok
    assert result.record is not None
    assert result.record.passed is True
    assert result.record.checks[0].required is False
    assert result.record.checks[0].passed is False
    assert result.record.checks[0].failure_code == "remote_task_failed"


def test_required_timeout_is_verification_failure(tmp_path: Path) -> None:
    write_plan(tmp_path)
    timeout = DomainFailure(
        code="remote_timeout",
        kind=FailureKind.REMOTE,
        message="timed out",
    )
    runner = FakeRunService(
        [outcome("run-1", exit_code=None, timed_out=True, failure=timeout), outcome("run-2")]
    )
    service = VerificationService(tmp_path, run_service=runner)  # type: ignore[arg-type]

    result = service.verify(VerificationRequest(codespace="space-one"))

    assert not result.ok
    assert result.failure is not None
    assert int(result.failure.exit_status) == 7
    assert result.record is not None
    assert result.record.checks[0].timed_out is True
    assert result.record.checks[0].failure_code == "remote_timeout"


def test_infrastructure_failure_aborts_without_becoming_check_assertion(tmp_path: Path) -> None:
    write_plan(tmp_path)
    failure = DomainFailure(
        code="transport_failure",
        kind=FailureKind.INFRASTRUCTURE,
        message="transport unavailable",
    )
    runner = FakeRunService(
        [outcome("run-1", exit_code=255, failure=failure), outcome("run-2")]
    )
    service = VerificationService(tmp_path, run_service=runner)  # type: ignore[arg-type]

    result = service.verify(VerificationRequest(codespace="space-one"))

    assert not result.ok
    assert result.failure == failure
    assert int(result.failure.exit_status) == 3
    assert result.record is not None
    assert result.record.complete is False
    assert len(result.record.checks) == 1
    assert len(runner.requests) == 1
