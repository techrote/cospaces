"""Durable checkpoint domain model."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
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
        raise ValueError("task ID must use 1-128 alphanumeric/._- characters and cannot traverse paths")
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
