from cospaces.domain.checkpoint import WorkingTreeState
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.checkpoint_service import CheckpointSaveRequest, CheckpointService
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbeResult
from cospaces.services.workspace_service import WorkspaceActionResult


class FakeProbe:
    def __init__(self, context: RepositoryContext) -> None:
        self.context = context
        self.calls = 0

    def capture(self) -> RepositoryProbeResult:
        self.calls += 1
        return RepositoryProbeResult(context=self.context)


class FakeWorkspace:
    def __init__(self, identity: WorkspaceIdentity) -> None:
        self.identity = identity
        self.calls: list[str] = []

    def describe(self, name: str) -> WorkspaceActionResult:
        self.calls.append(name)
        return WorkspaceActionResult(workspace=self.identity)


def context(*, head: str = "abc123", dirty: bool = True) -> RepositoryContext:
    return RepositoryContext(
        repository="owner/repo",
        ref="main",
        head=head,
        working_tree=WorkingTreeState(
            dirty=dirty,
            summary=(
                "modified=1;added=0;deleted=0;renamed=0;untracked=0;conflicted=0"
                if dirty
                else "modified=0;added=0;deleted=0;renamed=0;untracked=0;conflicted=0"
            ),
        ),
    )


def identity(*, ref: str = "main") -> WorkspaceIdentity:
    return WorkspaceIdentity(
        name="space-one",
        repository="owner/repo",
        ref=ref,
        state="available",
        display_name="space-one",
        machine="standard",
    )


def test_save_captures_bounded_git_context_t1_identity_and_t2_run_id(tmp_path) -> None:
    probe = FakeProbe(context())
    workspace = FakeWorkspace(identity())
    service = CheckpointService(tmp_path, probe=probe, workspace=workspace)  # type: ignore[arg-type]

    saved = service.save(
        CheckpointSaveRequest(
            task_id="issue-4",
            codespace="space-one",
            completed=("foundation", "workspace", "run"),
            current="checkpoint",
            next_step="verify",
            last_run_id="11111111-1111-4111-8111-111111111111",
            record_paths=(".cospaces/results/run-1.json",),
            notes="continue from T3",
        )
    )

    assert saved.ok
    assert saved.document is not None
    assert saved.document.repository == "owner/repo"
    assert saved.document.ref == "main"
    assert saved.document.head == "abc123"
    assert saved.document.working_tree is not None
    assert saved.document.working_tree.dirty is True
    assert saved.document.workspace == identity().to_dict()
    assert saved.document.records.last_run_id == "11111111-1111-4111-8111-111111111111"
    assert workspace.calls == ["space-one"]


def test_update_preserves_omitted_progress_and_created_time(tmp_path) -> None:
    probe = FakeProbe(context())
    service = CheckpointService(tmp_path, probe=probe)  # type: ignore[arg-type]
    first = service.save(
        CheckpointSaveRequest(
            task_id="issue-4",
            completed=("one",),
            current="two",
            next_step="three",
            notes="first",
        )
    )
    assert first.ok
    assert first.document is not None

    second = service.save(CheckpointSaveRequest(task_id="issue-4", notes="second"))

    assert second.ok
    assert second.document is not None
    assert second.document.created_at == first.document.created_at
    assert second.document.progress.completed == ("one",)
    assert second.document.progress.current == "two"
    assert second.document.progress.next_step == "three"
    assert second.document.notes == "second"
    assert second.previous_path is not None


def test_live_validation_reports_head_mismatch(tmp_path) -> None:
    probe = FakeProbe(context(head="old-head"))
    service = CheckpointService(tmp_path, probe=probe)  # type: ignore[arg-type]
    assert service.save(CheckpointSaveRequest(task_id="issue-4")).ok
    probe.context = context(head="new-head")

    validated = service.validate("issue-4", live=True)

    assert not validated.ok
    assert validated.failure is not None
    assert validated.failure.code == "checkpoint_context_mismatch"
    assert int(validated.failure.exit_status) == 4
    assert validated.live_checked is True
    assert [mismatch.field for mismatch in validated.mismatches] == ["head"]


def test_invalid_task_id_is_usage_failure(tmp_path) -> None:
    service = CheckpointService(tmp_path, probe=FakeProbe(context()))  # type: ignore[arg-type]

    result = service.save(CheckpointSaveRequest(task_id="../escape"))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "invalid_task_id"
    assert int(result.failure.exit_status) == 2


def test_no_git_mode_does_not_capture_environment_or_invent_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COSPACES_TEST_SECRET", "do-not-capture-this")
    service = CheckpointService(tmp_path, probe=FakeProbe(context()))  # type: ignore[arg-type]

    saved = service.save(
        CheckpointSaveRequest(
            task_id="issue-4",
            capture_git=False,
            notes="bounded note",
        )
    )

    assert saved.ok
    assert saved.document is not None
    assert saved.document.repository is None
    assert saved.document.ref is None
    assert saved.document.head is None
    assert saved.document.working_tree is None
    assert saved.path is not None
    serialized = saved.path.read_text(encoding="utf-8")
    assert "do-not-capture-this" not in serialized
    assert "COSPACES_TEST_SECRET" not in serialized


def test_show_and_list_return_valid_checkpoint(tmp_path) -> None:
    service = CheckpointService(tmp_path, probe=FakeProbe(context()))  # type: ignore[arg-type]
    assert service.save(CheckpointSaveRequest(task_id="issue-4")).ok

    shown = service.show("issue-4")
    listed = service.list()

    assert shown.ok
    assert shown.document is not None
    assert shown.document.task_id == "issue-4"
    assert [(entry.task_id, entry.status) for entry in listed.entries] == [("issue-4", "valid")]
