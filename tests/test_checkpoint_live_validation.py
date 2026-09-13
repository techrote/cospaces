from cospaces.domain.checkpoint import WorkingTreeState
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.checkpoint_service import CheckpointSaveRequest, CheckpointService
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbeResult
from cospaces.services.workspace_service import WorkspaceActionResult


class FakeProbe:
    def capture(self) -> RepositoryProbeResult:
        return RepositoryProbeResult(
            context=RepositoryContext(
                repository="owner/repo",
                ref="main",
                head="abc123",
                working_tree=WorkingTreeState(dirty=False, summary="clean"),
            )
        )


class MutableWorkspace:
    def __init__(self) -> None:
        self.ref = "main"

    def describe(self, name: str) -> WorkspaceActionResult:
        return WorkspaceActionResult(
            workspace=WorkspaceIdentity(
                name=name,
                repository="owner/repo",
                ref=self.ref,
                state="available",
                display_name=name,
                machine="standard",
            )
        )


def test_live_validation_reports_workspace_ref_mismatch(tmp_path) -> None:
    workspace = MutableWorkspace()
    service = CheckpointService(
        tmp_path,
        probe=FakeProbe(),  # type: ignore[arg-type]
        workspace=workspace,  # type: ignore[arg-type]
    )
    assert service.save(
        CheckpointSaveRequest(task_id="issue-4", codespace="space-one")
    ).ok
    workspace.ref = "feature"

    validated = service.validate("issue-4", live=True)

    assert not validated.ok
    assert validated.failure is not None
    assert validated.failure.code == "checkpoint_context_mismatch"
    assert [mismatch.field for mismatch in validated.mismatches] == ["workspace.ref"]
