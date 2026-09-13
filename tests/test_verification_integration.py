from pathlib import Path
from uuid import UUID

from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.checkpoint_service import CheckpointSaveRequest, CheckpointService
from cospaces.services.run_service import RunActionResult
from cospaces.services.verification_service import VerificationRequest, VerificationService


class FakeRunService:
    def __init__(self, outcomes: list[RunActionResult]) -> None:
        self.outcomes = outcomes
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.outcomes.pop(0)


def success(run_id: str) -> RunActionResult:
    target = WorkspaceIdentity(
        name="space-one",
        repository="owner/repo",
        ref="main",
        state="available",
        display_name="space-one",
        machine="standard",
    )
    return RunActionResult(
        workspace=target,
        record=RunRecord(
            run_id=run_id,
            argv=("example",),
            task_id="issue-5",
            correlation_id="verification",
            timeout_seconds=60,
            exit_code=0,
            timed_out=False,
            remote_completion="success",
            transport="gh-codespace-ssh",
            stdout="",
            stderr="",
            stderr_mixed=True,
            duration_seconds=0.01,
            started_at="2026-09-13T20:00:00Z",
            finished_at="2026-09-13T20:00:00.010000Z",
        ),
    )


def write_plan(root: Path) -> None:
    (root / ".cospaces.toml").write_text(
        "[verify.default]\n"
        "[[verify.default.checks]]\nname = \"one\"\ncommand = [\"example-one\"]\n"
        "[[verify.default.checks]]\nname = \"two\"\ncommand = [\"example-two\"]\n",
        encoding="utf-8",
    )


def test_unknown_plan_does_not_execute_remote_work(tmp_path: Path) -> None:
    write_plan(tmp_path)
    runner = FakeRunService([])
    service = VerificationService(tmp_path, run_service=runner)  # type: ignore[arg-type]

    result = service.verify(VerificationRequest(plan="missing", codespace="space-one"))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "verification_plan_not_found"
    assert runner.requests == []
