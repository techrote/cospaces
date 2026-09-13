"""Durable checkpoint domain model."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

SCHEMA = "cospaces.checkpoint/v1"
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_NOTE_CHARS = 4000
MAX_PROGRESS_CHARS = 1000
MAX_ITEM_CHARS = 500
MAX_ITEMS = 100
_WORKSPACE_KEYS = {"name", "repository", "ref", "state", "display_name", "machine"}


def validate_task_id(value: str) -> str:
    if value in {".", ".."} or TASK_ID_RE.fullmatch(value) is None:
        raise ValueError(
            "task ID must use 1-128 alphanumeric/._- characters and cannot traverse paths"
        )
    return value


@dataclass(frozen=True)
class WorkingTreeState:
    dirty: bool
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {"dirty": self.dirty, "summary": self.summary}


@dataclass(frozen=True)
class ProgressState:
    completed: tuple[str, ...] = ()
    current: str | None = None
    next_step: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "completed": list(self.completed),
            "current": self.current,
            "next": self.next_step,
        }


@dataclass(frozen=True)
class RecordReferences:
    last_run_id: str | None = None
    last_verification_id: str | None = None
    paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "last_run_id": self.last_run_id,
            "last_verification_id": self.last_verification_id,
            "paths": list(self.paths),
        }


@dataclass(frozen=True)
class CheckpointDocument:
    task_id: str
    created_at: str
    updated_at: str
    repository: str | None = None
    ref: str | None = None
    head: str | None = None
    workspace: Mapping[str, object] | None = None
    working_tree: WorkingTreeState | None = None
    progress: ProgressState = ProgressState()
    records: RecordReferences = RecordReferences()
    notes: str = ""
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "repository": self.repository,
            "ref": self.ref,
            "head": self.head,
            "workspace": dict(self.workspace) if self.workspace is not None else None,
            "working_tree": self.working_tree.to_dict() if self.working_tree is not None else None,
            "progress": self.progress.to_dict(),
            "records": self.records.to_dict(),
            "notes": self.notes,
        }


def _bounded_text(value: Any, label: str, limit: int, *, allow_none: bool = True) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if len(value) > limit:
        raise ValueError(f"{label} exceeds {limit} characters")
    return value


def _timestamp(value: Any, label: str) -> str:
    text = _bounded_text(value, label, 64, allow_none=False)
    assert text is not None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return text


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"{label} exceeds {MAX_ITEMS} items")
    items: list[str] = []
    for item in value:
        text = _bounded_text(item, f"{label} item", MAX_ITEM_CHARS, allow_none=False)
        assert text is not None
        items.append(text)
    return tuple(items)


def _workspace(value: Any) -> Mapping[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("workspace must be an object or null")
    unknown = set(value) - _WORKSPACE_KEYS
    if unknown:
        raise ValueError(f"workspace contains unsupported keys: {sorted(unknown)}")
    result: dict[str, object] = {}
    for key in sorted(_WORKSPACE_KEYS):
        item = value.get(key)
        if item is not None and not isinstance(item, str):
            raise ValueError(f"workspace.{key} must be a string or null")
        if isinstance(item, str) and len(item) > MAX_ITEM_CHARS:
            raise ValueError(f"workspace.{key} exceeds {MAX_ITEM_CHARS} characters")
        result[key] = item
    if not isinstance(result.get("name"), str) or not result["name"]:
        raise ValueError("workspace.name is required when workspace is present")
    return result


def checkpoint_from_dict(payload: Mapping[str, Any]) -> CheckpointDocument:
    schema = payload.get("schema")
    if schema != SCHEMA:
        raise ValueError(f"unsupported checkpoint schema: {schema!r}")

    raw_task = payload.get("task_id")
    if not isinstance(raw_task, str):
        raise ValueError("task_id must be a string")
    task_id = validate_task_id(raw_task)
    created_at = _timestamp(payload.get("created_at"), "created_at")
    updated_at = _timestamp(payload.get("updated_at"), "updated_at")

    working_payload = payload.get("working_tree")
    working_tree: WorkingTreeState | None = None
    if working_payload is not None:
        if not isinstance(working_payload, Mapping):
            raise ValueError("working_tree must be an object or null")
        if set(working_payload) - {"dirty", "summary"}:
            raise ValueError("working_tree contains unsupported keys")
        dirty = working_payload.get("dirty")
        if not isinstance(dirty, bool):
            raise ValueError("working_tree.dirty must be a boolean")
        summary = _bounded_text(
            working_payload.get("summary"),
            "working_tree.summary",
            MAX_PROGRESS_CHARS,
            allow_none=False,
        )
        assert summary is not None
        working_tree = WorkingTreeState(dirty=dirty, summary=summary)

    progress_payload = payload.get("progress")
    if not isinstance(progress_payload, Mapping):
        raise ValueError("progress must be an object")
    if set(progress_payload) - {"completed", "current", "next"}:
        raise ValueError("progress contains unsupported keys")
    completed = _string_tuple(progress_payload.get("completed", []), "progress.completed")
    current = _bounded_text(progress_payload.get("current"), "progress.current", MAX_PROGRESS_CHARS)
    next_step = _bounded_text(progress_payload.get("next"), "progress.next", MAX_PROGRESS_CHARS)

    records_payload = payload.get("records")
    if not isinstance(records_payload, Mapping):
        raise ValueError("records must be an object")
    if set(records_payload) - {"last_run_id", "last_verification_id", "paths"}:
        raise ValueError("records contains unsupported keys")
    last_run_id = _bounded_text(
        records_payload.get("last_run_id"),
        "records.last_run_id",
        MAX_ITEM_CHARS,
    )
    last_verification_id = _bounded_text(
        records_payload.get("last_verification_id"),
        "records.last_verification_id",
        MAX_ITEM_CHARS,
    )
    paths = _string_tuple(records_payload.get("paths", []), "records.paths")

    notes = _bounded_text(payload.get("notes", ""), "notes", MAX_NOTE_CHARS, allow_none=False)
    assert notes is not None
    return CheckpointDocument(
        task_id=task_id,
        created_at=created_at,
        updated_at=updated_at,
        repository=_bounded_text(payload.get("repository"), "repository", MAX_ITEM_CHARS),
        ref=_bounded_text(payload.get("ref"), "ref", MAX_ITEM_CHARS),
        head=_bounded_text(payload.get("head"), "head", MAX_ITEM_CHARS),
        workspace=_workspace(payload.get("workspace")),
        working_tree=working_tree,
        progress=ProgressState(completed=completed, current=current, next_step=next_step),
        records=RecordReferences(
            last_run_id=last_run_id,
            last_verification_id=last_verification_id,
            paths=paths,
        ),
        notes=notes,
    )
