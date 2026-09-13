"""Repository-declared verification orchestration over T2 runs."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.results import utc_now
from cospaces.domain.run import RunRequest
from cospaces.domain.verification import (
    VerificationCheck,
    VerificationCheckRecord,
    VerificationRecord,
)
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbe
from cospaces.services.run_service import RunActionResult, RunService
from cospaces.verification_command import build_check_argv
from cospaces.verification_config import load_verification_plan


@dataclass(frozen=True)
class VerificationRequest:
    plan: str = "default"
    codespace: str | None = None
    repository: str | None = None
    ref: str | None = None
    task_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class VerificationActionResult:
    record: VerificationRecord | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


class VerificationService:
    def __init__(
        self,
        root: Path,
        *,
        run_service: RunService | None = None,
        probe: RepositoryProbe | None = None,
    ) -> None:
        self.root = root
        self._run = run_service or RunService()
        self._probe = probe or RepositoryProbe(root)

    def _repository_context(self) -> RepositoryContext | None:
        result = self._probe.capture()
        return result.context if result.ok else None

    @staticmethod
    def _check_record(
        check: VerificationCheck,
        result: RunActionResult,
    ) -> VerificationCheckRecord:
        run = result.record
        return VerificationCheckRecord(
            name=check.name,
            required=check.required,
            passed=result.failure is None,
            timed_out=run.timed_out,
            run_id=run.run_id,
            exit_code=run.exit_code,
            remote_completion=run.remote_completion,
            duration_ms=max(0, round(run.duration_seconds * 1000)),
            failure_code=result.failure.code if result.failure is not None else None,
            command=check.command,
            working_directory=check.working_directory,
            environment_keys=tuple(key for key, _value in check.environment),
        )

    @staticmethod
    def _record(
        *,
        verification_id: str,
        request: VerificationRequest,
        repository: str | None,
        ref: str | None,
        head: str | None,
        workspace: Mapping[str, object] | None,
        started_at: str,
        complete: bool,
        passed: bool,
        checks: list[VerificationCheckRecord],
    ) -> VerificationRecord:
        return VerificationRecord(
            verification_id=verification_id,
            plan=request.plan,
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            repository=repository,
            ref=ref,
            head=head,
            workspace=workspace,
            started_at=started_at,
            finished_at=utc_now(),
            complete=complete,
            passed=passed,
            checks=tuple(checks),
        )

    @staticmethod
    def _head_matches_workspace(
        context: RepositoryContext | None,
        repository: str | None,
        ref: str | None,
    ) -> bool:
        if context is None or repository is None or ref is None:
            return False
        return repository == context.repository and ref == context.ref

    def verify(self, request: VerificationRequest) -> VerificationActionResult:
        loaded = load_verification_plan(self.root, request.plan)
        if not loaded.ok:
            return VerificationActionResult(failure=loaded.failure)
        assert loaded.plan is not None
        plan = loaded.plan

        if request.codespace is None and request.repository is None:
            return VerificationActionResult(
                failure=DomainFailure(
                    code="workspace_target_required",
                    kind=FailureKind.USAGE,
                    message="Verification requires --codespace or --repo",
                )
            )

        verification_id = str(uuid4())
        started_at = utc_now()
        context = self._repository_context()
        provenance_repository = request.repository
        provenance_ref = request.ref
        head = (
            context.head
            if self._head_matches_workspace(context, request.repository, request.ref)
            else None
        )

        selected_codespace = request.codespace
        workspace_payload: Mapping[str, object] | None = None
        check_records: list[VerificationCheckRecord] = []
        required_failed = False

        for check in plan.checks:
            run_result = self._run.execute(
                RunRequest(
                    argv=build_check_argv(check),
                    codespace=selected_codespace,
                    repository=request.repository,
                    ref=request.ref,
                    timeout_seconds=check.timeout_seconds,
                    task_id=request.task_id,
                    correlation_id=verification_id,
                )
            )
            check_record = self._check_record(check, run_result)
            check_records.append(check_record)

            if run_result.workspace is not None:
                if selected_codespace is None:
                    selected_codespace = run_result.workspace.name
                workspace_payload = run_result.workspace.to_dict()
                if run_result.workspace.repository is not None:
                    provenance_repository = run_result.workspace.repository
                if run_result.workspace.ref is not None:
                    provenance_ref = run_result.workspace.ref
                if self._head_matches_workspace(
                    context,
                    run_result.workspace.repository,
                    run_result.workspace.ref,
                ):
                    assert context is not None
                    head = context.head
                else:
                    head = None

            if run_result.failure is not None:
                if run_result.failure.kind is not FailureKind.REMOTE:
                    record = self._record(
                        verification_id=verification_id,
                        request=request,
                        repository=provenance_repository,
                        ref=provenance_ref,
                        head=head,
                        workspace=workspace_payload,
                        started_at=started_at,
                        complete=False,
                        passed=False,
                        checks=check_records,
                    )
                    return VerificationActionResult(
                        record=record,
                        failure=run_result.failure,
                    )
                if check.required:
                    required_failed = True

        passed = not required_failed
        record = self._record(
            verification_id=verification_id,
            request=request,
            repository=provenance_repository,
            ref=provenance_ref,
            head=head,
            workspace=workspace_payload,
            started_at=started_at,
            complete=True,
            passed=passed,
            checks=check_records,
        )
        if not passed:
            failed_count = sum(
                1 for check in check_records if check.required and not check.passed
            )
            return VerificationActionResult(
                record=record,
                failure=DomainFailure(
                    code="verification_failed",
                    kind=FailureKind.VERIFICATION,
                    message=f"{failed_count} required verification check(s) failed",
                ),
            )
        return VerificationActionResult(record=record)
