from pathlib import Path
from uuid import UUID

from cospaces.domain.checkpoint import (
    CheckpointDocument,
    RecordReferences,
    WorkingTreeState,
    checkpoint_from_dict,
)
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbeResult
from cospaces.services.run_service import RunActionResult
from cospaces.services.verification_service import VerificationRequest, VerificationService


class FakeRunService:
    def __init__(self, outcomes: list[RunActionResult]) -> None:
        self.outcomes = outcomes
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.outcomes.pop(0)


class DifferentLocalProbe:
    def capture(self) -> RepositoryProbeResult:
        return RepositoryProbeResult(
            context=RepositoryContext(
                repository="controller/repo",
                ref="controller-branch",
                head="controller-head",
                working_tree=WorkingTreeState(dirty=False, summary="clean"),
            )
        )


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


def test_explicit_codespace_does_not_inherit_controller_repo_as_target(tmp_path: Path) -> None:
    write_plan(tmp_path)
    runner = FakeRunService([success("r1"), success("r2")])
    service = VerificationService(
        tmp_path,
        run_service=runner,  # type: ignore[arg-type]
        probe=DifferentLocalProbe(),  # type: ignore[arg-type]
    )

    result = service.verify(VerificationRequest(codespace="space-one"))

    assert result.ok
    assert all(request.repository is None for request in runner.requests)
    assert result.record is not None
    assert result.record.repository == "owner/repo"
    assert result.record.ref == "main"
    assert result.record.head is None


def test_verification_ids_are_unique_and_fit_t3_reference_schema(tmp_path: Path) -> None:
    write_plan(tmp_path)
    runner = FakeRunService([success("r1"), success("r2"), success("r3"), success("r4")])
    service = VerificationService(tmp_path, run_service=runner)  # type: ignore[arg-type]

    first = service.verify(VerificationRequest(codespace="space-one", task_id="issue-5"))
    second = service.verify(VerificationRequest(codespace="space-one", task_id="issue-5"))

    assert first.record is not None
    assert second.record is not None
    verification_id = first.record.verification_id
    assert verification_id != second.record.verification_id
    assert UUID(verification_id)
    checkpoint = CheckpointDocument(
        task_id="issue-5",
        created_at="2026-09-13T20:00:00Z",
        updated_at="2026-09-13T20:00:01Z",
        records=RecordReferences(last_verification_id=verification_id),
    )
    parsed = checkpoint_from_dict(checkpoint.to_dict())
    assert parsed.records.last_verification_id == verification_id
