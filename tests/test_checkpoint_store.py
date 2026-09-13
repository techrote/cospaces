import json

from cospaces.domain.checkpoint import CheckpointDocument
from cospaces.services.checkpoint_store import CheckpointStore


def document(task: str = "issue-4", *, updated: str = "2026-09-13T19:01:00Z", notes: str = "one") -> CheckpointDocument:
    return CheckpointDocument(
        task_id=task,
        created_at="2026-09-13T19:00:00Z",
        updated_at=updated,
        repository="owner/repo",
        ref="main",
        head="abc123",
        notes=notes,
    )


def test_fresh_save_and_read(tmp_path) -> None:
    store = CheckpointStore(tmp_path)

    saved = store.save(document())
    loaded = store.read("issue-4")

    assert saved.ok
    assert saved.previous_path is None
    assert saved.path == tmp_path / ".cospaces" / "checkpoints" / "issue-4.json"
    assert loaded.ok
    assert loaded.document is not None
    assert loaded.document.notes == "one"


def test_update_retains_one_previous_valid_revision(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    first = document(notes="first")
    second = document(updated="2026-09-13T19:02:00Z", notes="second")

    assert store.save(first).ok
    saved = store.save(second)

    assert saved.ok
    assert saved.previous_path == tmp_path / ".cospaces" / "checkpoints" / ".history" / "issue-4.json"
    previous = json.loads(saved.previous_path.read_text(encoding="utf-8"))
    current = json.loads(saved.path.read_text(encoding="utf-8"))
    assert previous["notes"] == "first"
    assert current["notes"] == "second"


def test_corrupt_current_is_not_overwritten(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    path = store.checkpoint_path("issue-4")
    path.parent.mkdir(parents=True)
    path.write_text("{not-json", encoding="utf-8")

    saved = store.save(document(notes="replacement"))

    assert not saved.ok
    assert saved.failure is not None
    assert saved.failure.code == "checkpoint_malformed"
    assert path.read_text(encoding="utf-8") == "{not-json"


def test_unsupported_schema_is_reported(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    path = store.checkpoint_path("issue-4")
    path.parent.mkdir(parents=True)
    payload = document().to_dict()
    payload["schema"] = "cospaces.checkpoint/v999"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.read("issue-4")

    assert not loaded.ok
    assert loaded.failure is not None
    assert loaded.failure.code == "unsupported_checkpoint_schema"


def test_list_surfaces_invalid_current_files(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    assert store.save(document("good")).ok
    bad = store.checkpoint_path("bad")
    bad.write_text("[]", encoding="utf-8")

    entries = store.list_entries()

    assert [(entry.task_id, entry.status) for entry in entries] == [
        ("bad", "invalid"),
        ("good", "valid"),
    ]


def test_atomic_replace_failure_does_not_leave_current_file(tmp_path, monkeypatch) -> None:
    store = CheckpointStore(tmp_path)

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("cospaces.services.checkpoint_store.os.replace", fail_replace)

    saved = store.save(document())

    assert not saved.ok
    assert saved.failure is not None
    assert saved.failure.code == "checkpoint_write_failed"
    assert not store.checkpoint_path("issue-4").exists()
