"""Atomic repository-local checkpoint persistence."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cospaces.domain.checkpoint import SCHEMA, CheckpointDocument, checkpoint_from_dict, validate_task_id
from cospaces.domain.contracts import DomainFailure, FailureKind


@dataclass(frozen=True)
class CheckpointReadResult:
    document: CheckpointDocument | None = None
    path: Path | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(frozen=True)
class CheckpointSaveResult:
    document: CheckpointDocument | None = None
    path: Path | None = None
    previous_path: Path | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


@dataclass(frozen=True)
class CheckpointListEntry:
    task_id: str
    status: str
    updated_at: str | None
    path: Path
    error_code: str | None = None

    def to_dict(self, root: Path) -> dict[str, object]:
        try:
            display_path = str(self.path.relative_to(root))
        except ValueError:
            display_path = str(self.path)
        return {
            "task_id": self.task_id,
            "status": self.status,
            "updated_at": self.updated_at,
            "path": display_path,
            "error_code": self.error_code,
        }


class CheckpointStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / ".cospaces" / "checkpoints"

    def checkpoint_path(self, task_id: str) -> Path:
        return self.directory / f"{validate_task_id(task_id)}.json"

    def previous_path(self, task_id: str) -> Path:
        return self.directory / f"{validate_task_id(task_id)}.previous.json"

    @staticmethod
    def _failure(code: str, message: str) -> DomainFailure:
        return DomainFailure(code=code, kind=FailureKind.PERSISTENCE, message=message)

    def _read_path(self, path: Path, expected_task: str | None = None) -> CheckpointReadResult:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return CheckpointReadResult(
                path=path,
                failure=self._failure("checkpoint_not_found", "Checkpoint does not exist"),
            )
        except OSError:
            return CheckpointReadResult(
                path=path,
                failure=self._failure("checkpoint_read_failed", "Checkpoint could not be read"),
            )
        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError:
            return CheckpointReadResult(
                path=path,
                failure=self._failure("checkpoint_malformed", "Checkpoint is not valid JSON"),
            )
        if not isinstance(payload, dict):
            return CheckpointReadResult(
                path=path,
                failure=self._failure("checkpoint_invalid", "Checkpoint root must be an object"),
            )
        if payload.get("schema") != SCHEMA:
            return CheckpointReadResult(
                path=path,
                failure=self._failure(
                    "unsupported_checkpoint_schema",
                    f"Unsupported checkpoint schema: {payload.get('schema')!r}",
                ),
            )
        try:
            document = checkpoint_from_dict(payload)
        except ValueError as exc:
            return CheckpointReadResult(
                path=path,
                failure=self._failure("checkpoint_invalid", str(exc)),
            )
        if expected_task is not None and document.task_id != expected_task:
            return CheckpointReadResult(
                path=path,
                failure=self._failure(
                    "checkpoint_task_mismatch",
                    "Checkpoint task ID does not match its requested path",
                ),
            )
        return CheckpointReadResult(document=document, path=path)

    def read(self, task_id: str) -> CheckpointReadResult:
        try:
            path = self.checkpoint_path(task_id)
        except ValueError as exc:
            return CheckpointReadResult(
                failure=DomainFailure(
                    code="invalid_task_id",
                    kind=FailureKind.USAGE,
                    message=str(exc),
                )
            )
        return self._read_path(path, expected_task=task_id)

    def _atomic_write(self, path: Path, text: str) -> DomainFailure | None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                text=True,
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        except OSError:
            return self._failure("checkpoint_write_failed", "Checkpoint atomic write failed")
        return None

    @staticmethod
    def _serialized(document: CheckpointDocument) -> str:
        return json.dumps(document.to_dict(), indent=2, sort_keys=True) + "\n"

    def save(self, document: CheckpointDocument) -> CheckpointSaveResult:
        try:
            path = self.checkpoint_path(document.task_id)
            previous = self.previous_path(document.task_id)
        except ValueError as exc:
            return CheckpointSaveResult(
                failure=DomainFailure(
                    code="invalid_task_id",
                    kind=FailureKind.USAGE,
                    message=str(exc),
                )
            )

        if path.exists():
            current = self._read_path(path, expected_task=document.task_id)
            if not current.ok:
                return CheckpointSaveResult(path=path, previous_path=previous, failure=current.failure)
            assert current.document is not None
            backup_failure = self._atomic_write(previous, self._serialized(current.document))
            if backup_failure is not None:
                return CheckpointSaveResult(
                    path=path,
                    previous_path=previous,
                    failure=backup_failure,
                )

        write_failure = self._atomic_write(path, self._serialized(document))
        if write_failure is not None:
            return CheckpointSaveResult(path=path, previous_path=previous, failure=write_failure)
        verified = self._read_path(path, expected_task=document.task_id)
        if not verified.ok:
            return CheckpointSaveResult(path=path, previous_path=previous, failure=verified.failure)
        return CheckpointSaveResult(
            document=verified.document,
            path=path,
            previous_path=previous if previous.exists() else None,
        )

    def list_entries(self) -> tuple[CheckpointListEntry, ...]:
        if not self.directory.exists():
            return ()
        entries: list[CheckpointListEntry] = []
        try:
            paths = sorted(self.directory.glob("*.json"))
        except OSError:
            return ()
        for path in paths:
            if path.name.endswith(".previous.json"):
                continue
            task_id = path.name[:-5]
            loaded = self._read_path(path, expected_task=task_id)
            if loaded.ok:
                assert loaded.document is not None
                entries.append(
                    CheckpointListEntry(
                        task_id=task_id,
                        status="valid",
                        updated_at=loaded.document.updated_at,
                        path=path,
                    )
                )
            else:
                entries.append(
                    CheckpointListEntry(
                        task_id=task_id,
                        status="invalid",
                        updated_at=None,
                        path=path,
                        error_code=loaded.failure.code if loaded.failure is not None else "unknown",
                    )
                )
        return tuple(entries)
