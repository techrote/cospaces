"""Checkpoint save/show/list/validation orchestration."""

from dataclasses import dataclass
from pathlib import Path

from cospaces.domain.checkpoint import (
    CheckpointDocument,
    ProgressState,
    RecordReferences,
    checkpoint_from_dict,
    validate_task_id,
)
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.results import utc_now
from cospaces.services.checkpoint_store import (
    CheckpointListEntry,
    CheckpointStore,
)
from cospaces.services.repository_probe import RepositoryProbe
from cospaces.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class CheckpointSaveRequest:
    task_id: str
    repository: str | None = None
    ref: str | None = None
    head: str | None = None
    codespace: str | None = None
    capture_git: bool = True
    completed: tuple[str, ...] | None = None
    current: str | None = None
    next_step: str | None = None
    last_run_id: str | None = None
    last_verification_id: str | None = None
    record_paths: tuple[str, ...] | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ContextMismatch:
    field: str
    expected: str | None
    actual: str | None

    def to_dict(self) -> dict[str, object]:
        return {"field": self.field, "expected": self.expected, "actual": self.actual}


@dataclass(frozen=True)
class CheckpointActionResult:
    document: CheckpointDocument | None = None
    entries: tuple[CheckpointListEntry, ...] = ()
    path: Path | None = None
    previous_path: Path | None = None
    mismatches: tuple[ContextMismatch, ...] = ()
    live_checked: bool = False
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


class CheckpointService:
    def __init__(
        self,
        root: Path,
        *,
        store: CheckpointStore | None = None,
        probe: RepositoryProbe | None = None,
        workspace: WorkspaceService | None = None,
    ) -> None:
        self.root = root
        self._store = store or CheckpointStore(root)
        self._probe = probe or RepositoryProbe(root)
        self._workspace = workspace or WorkspaceService()

    @staticmethod
    def _usage(code: str, message: str) -> CheckpointActionResult:
        return CheckpointActionResult(
            failure=DomainFailure(code=code, kind=FailureKind.USAGE, message=message)
        )

    def save(self, request: CheckpointSaveRequest) -> CheckpointActionResult:
        try:
            validate_task_id(request.task_id)
        except ValueError as exc:
            return self._usage("invalid_task_id", str(exc))

        existing_result = self._store.read(request.task_id)
        existing = None
        if existing_result.ok:
            existing = existing_result.document
        elif (
            existing_result.failure is None
            or existing_result.failure.code != "checkpoint_not_found"
        ):
            return CheckpointActionResult(failure=existing_result.failure)

        context = None
        if request.capture_git:
            probed = self._probe.capture()
            if not probed.ok:
                return CheckpointActionResult(failure=probed.failure)
            context = probed.context
            assert context is not None

        workspace_payload = existing.workspace if existing is not None else None
        if request.codespace is not None:
            described = self._workspace.describe(request.codespace)
            if not described.ok:
                return CheckpointActionResult(failure=described.failure)
            assert described.workspace is not None
            workspace_payload = described.workspace.to_dict()

        now = utc_now()
        existing_progress = existing.progress if existing is not None else ProgressState()
        existing_records = existing.records if existing is not None else RecordReferences()
        repository = request.repository
        ref = request.ref
        head = request.head
        working_tree = existing.working_tree if existing is not None else None
        if context is not None:
            repository = repository if repository is not None else context.repository
            ref = ref if ref is not None else context.ref
            head = head if head is not None else context.head
            working_tree = context.working_tree
        elif existing is not None:
            repository = repository if repository is not None else existing.repository
            ref = ref if ref is not None else existing.ref
            head = head if head is not None else existing.head

        document = CheckpointDocument(
            task_id=request.task_id,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
            repository=repository,
            ref=ref,
            head=head,
            workspace=workspace_payload,
            working_tree=working_tree,
            progress=ProgressState(
                completed=request.completed
                if request.completed is not None
                else existing_progress.completed,
                current=(request.current if request.current is not None else existing_progress.current),
                next_step=request.next_step
                if request.next_step is not None
                else existing_progress.next_step,
            ),
            records=RecordReferences(
                last_run_id=request.last_run_id
                if request.last_run_id is not None
                else existing_records.last_run_id,
                last_verification_id=request.last_verification_id
                if request.last_verification_id is not None
                else existing_records.last_verification_id,
                paths=request.record_paths
                if request.record_paths is not None
                else existing_records.paths,
            ),
            notes=(request.notes if request.notes is not None else (existing.notes if existing else "")),
        )
        try:
            validated = checkpoint_from_dict(document.to_dict())
        except ValueError as exc:
            return self._usage("invalid_checkpoint_input", str(exc))

        saved = self._store.save(validated)
        if not saved.ok:
            return CheckpointActionResult(
                path=saved.path,
                previous_path=saved.previous_path,
                failure=saved.failure,
            )
        return CheckpointActionResult(
            document=saved.document,
            path=saved.path,
            previous_path=saved.previous_path,
        )

    def show(self, task_id: str) -> CheckpointActionResult:
        loaded = self._store.read(task_id)
        return CheckpointActionResult(
            document=loaded.document,
            path=loaded.path,
            failure=loaded.failure,
        )

    def list(self) -> CheckpointActionResult:
        return CheckpointActionResult(entries=self._store.list_entries())

    @staticmethod
    def _compare(
        mismatches: list[ContextMismatch],
        field: str,
        expected: object,
        actual: object,
    ) -> None:
        if expected is None:
            return
        expected_text = str(expected)
        actual_text = str(actual) if actual is not None else None
        if actual_text != expected_text:
            mismatches.append(
                ContextMismatch(field=field, expected=expected_text, actual=actual_text)
            )

    def validate(
        self,
        task_id: str,
        *,
        live: bool = False,
        codespace: str | None = None,
    ) -> CheckpointActionResult:
        loaded = self._store.read(task_id)
        if not loaded.ok:
            return CheckpointActionResult(path=loaded.path, failure=loaded.failure)
        document = loaded.document
        assert document is not None
        if not live:
            return CheckpointActionResult(document=document, path=loaded.path)

        probed = self._probe.capture()
        if not probed.ok:
            return CheckpointActionResult(
                document=document,
                path=loaded.path,
                live_checked=True,
                failure=probed.failure,
            )
        context = probed.context
        assert context is not None
        mismatches: list[ContextMismatch] = []
        self._compare(mismatches, "repository", document.repository, context.repository)
        self._compare(mismatches, "ref", document.ref, context.ref)
        self._compare(mismatches, "head", document.head, context.head)

        if document.workspace is not None:
            stored_name = document.workspace.get("name")
            target_name = codespace or (str(stored_name) if stored_name is not None else None)
            if target_name is not None:
                described = self._workspace.describe(target_name)
                if not described.ok:
                    return CheckpointActionResult(
                        document=document,
                        path=loaded.path,
                        live_checked=True,
                        failure=described.failure,
                    )
                assert described.workspace is not None
                live_workspace = described.workspace.to_dict()
                self._compare(mismatches, "workspace.name", stored_name, live_workspace.get("name"))
                self._compare(
                    mismatches,
                    "workspace.repository",
                    document.workspace.get("repository"),
                    live_workspace.get("repository"),
                )
                self._compare(
                    mismatches,
                    "workspace.ref",
                    document.workspace.get("ref"),
                    live_workspace.get("ref"),
                )
                self._compare(
                    mismatches,
                    "workspace.machine",
                    document.workspace.get("machine"),
                    live_workspace.get("machine"),
                )

        if mismatches:
            return CheckpointActionResult(
                document=document,
                path=loaded.path,
                mismatches=tuple(mismatches),
                live_checked=True,
                failure=DomainFailure(
                    code="checkpoint_context_mismatch",
                    kind=FailureKind.SELECTION,
                    message="Live repository/workspace context does not match the checkpoint",
                ),
            )
        return CheckpointActionResult(
            document=document,
            path=loaded.path,
            live_checked=True,
        )
