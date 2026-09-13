from pathlib import Path

from cospaces.domain.checkpoint import WorkingTreeState
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.checkpoint_service import CheckpointSaveRequest, CheckpointService
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbeResult
from cospaces.services.workspace_service import WorkspaceActionResult


class StableProbe:
    def capture(self) -> RepositoryProbeResult:
        return RepositoryProbeResult(
            context=RepositoryContext(
                repository="owner/repo",
                ref="feature/hardening",
                head="abc123",
                working_tree=WorkingTreeState(dirty=False, summary="clean"),
            )
        )


class StableWorkspace:
    def describe(self, name: str) -> WorkspaceActionResult:
        return WorkspaceActionResult(
            workspace=WorkspaceIdentity(
                name=name,
                repository="owner/repo",
                ref="feature/hardening",
                state="shutdown",
                display_name="hardening-space",
                machine="standardLinux32gb",
            )
        )


def test_checkpoint_survives_controller_reconstruction_without_executing_next(tmp_path: Path) -> None:
    initial = CheckpointService(
        tmp_path,
        probe=StableProbe(),  # type: ignore[arg-type]
        workspace=StableWorkspace(),  # type: ignore[arg-type]
    )
    saved = initial.save(
        CheckpointSaveRequest(
            task_id="hardening-cycle",
            repository="owner/repo",
            ref="feature/hardening",
            head="abc123",
            codespace="space-one",
            capture_git=False,
            completed=("workspace selected", "remote run complete"),
            current="checkpointed before controller loss",
            next_step="DO-NOT-EXECUTE automatically",
            last_run_id="run-123",
            last_verification_id="verify-456",
            record_paths=("evidence/run-123.json",),
            notes="controller may be reconstructed safely",
        )
    )

    assert saved.ok
    assert saved.document is not None

    reconstructed = CheckpointService(
        tmp_path,
        probe=StableProbe(),  # type: ignore[arg-type]
        workspace=StableWorkspace(),  # type: ignore[arg-type]
    )
    shown = reconstructed.show("hardening-cycle")
    validated = reconstructed.validate("hardening-cycle", live=True)

    assert shown.ok
    assert shown.document is not None
    assert shown.document.progress.next_step == "DO-NOT-EXECUTE automatically"
    assert shown.document.records.last_run_id == "run-123"
    assert shown.document.records.last_verification_id == "verify-456"
    assert shown.document.records.paths == ("evidence/run-123.json",)
    assert shown.document.workspace is not None
    assert shown.document.workspace["name"] == "space-one"
    assert validated.ok
    assert validated.live_checked is True
    assert validated.mismatches == ()
