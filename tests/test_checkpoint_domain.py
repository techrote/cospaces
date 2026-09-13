from cospaces.domain.checkpoint import (
    SCHEMA,
    CheckpointDocument,
    ProgressState,
    RecordReferences,
    WorkingTreeState,
    checkpoint_from_dict,
    validate_task_id,
)


def document() -> CheckpointDocument:
    return CheckpointDocument(
        task_id="issue-4",
        created_at="2026-09-13T19:00:00Z",
        updated_at="2026-09-13T19:01:00Z",
        repository="owner/repo",
        ref="main",
        head="abc123",
        workspace={
            "name": "space-one",
            "repository": "owner/repo",
            "ref": "main",
            "state": "available",
            "display_name": "space-one",
            "machine": "standard",
        },
        working_tree=WorkingTreeState(dirty=True, summary="modified=1;untracked=0"),
        progress=ProgressState(completed=("one",), current="two", next_step="three"),
        records=RecordReferences(last_run_id="run-1", paths=("evidence/run-1.json",)),
        notes="continue",
    )


def test_checkpoint_round_trip_preserves_schema_and_t2_reference() -> None:
    parsed = checkpoint_from_dict(document().to_dict())

    assert parsed.schema == SCHEMA
    assert parsed.task_id == "issue-4"
    assert parsed.workspace is not None
    assert parsed.workspace["name"] == "space-one"
    assert parsed.records.last_run_id == "run-1"
    assert parsed.progress.next_step == "three"


def test_task_ids_reject_path_traversal_and_separators() -> None:
    for value in ("../escape", "a/b", "a\\b", "..", ".", ""):
        try:
            validate_task_id(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe task ID accepted: {value}")


def test_checkpoint_rejects_unsupported_schema() -> None:
    payload = document().to_dict()
    payload["schema"] = "cospaces.checkpoint/v999"

    try:
        checkpoint_from_dict(payload)
    except ValueError as exc:
        assert "unsupported checkpoint schema" in str(exc)
    else:
        raise AssertionError("unsupported schema accepted")


def test_workspace_rejects_unexpected_keys() -> None:
    payload = document().to_dict()
    workspace = dict(payload["workspace"])  # type: ignore[arg-type]
    workspace["token"] = "must-not-be-stored"
    payload["workspace"] = workspace

    try:
        checkpoint_from_dict(payload)
    except ValueError as exc:
        assert "unsupported keys" in str(exc)
    else:
        raise AssertionError("unexpected workspace key accepted")


def test_notes_are_bounded() -> None:
    payload = document().to_dict()
    payload["notes"] = "x" * 4001

    try:
        checkpoint_from_dict(payload)
    except ValueError as exc:
        assert "notes exceeds" in str(exc)
    else:
        raise AssertionError("oversized notes accepted")
