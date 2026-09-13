"""Remote run orchestration using deterministic workspace targeting."""

import time
from dataclasses import dataclass
from uuid import uuid4

from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.results import utc_now
from cospaces.domain.run import RunRecord, RunRequest
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.run_transport import CodespaceSshTransport, TRANSPORT_NAME
from cospaces.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class RunActionResult:
    record: RunRecord
    workspace: WorkspaceIdentity | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


class RunService:
    def __init__(
        self,
        workspace: WorkspaceService | None = None,
        transport: CodespaceSshTransport | None = None,
    ) -> None:
        self._workspace = workspace or WorkspaceService()
        self._transport = transport or CodespaceSshTransport()

    def _record(
        self,
        *,
        run_id: str,
        request: RunRequest,
        started_at: str,
        started_clock: float,
        exit_code: int | None = None,
        timed_out: bool = False,
        remote_completion: str = "not_started",
        stdout: str = "",
        stderr: str = "",
        stderr_mixed: bool = False,
    ) -> RunRecord:
        return RunRecord(
            run_id=run_id,
            argv=request.argv,
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            timeout_seconds=request.timeout_seconds,
            exit_code=exit_code,
            timed_out=timed_out,
            remote_completion=remote_completion,
            transport=TRANSPORT_NAME,
            stdout=stdout,
            stderr=stderr,
            stderr_mixed=stderr_mixed,
            duration_seconds=max(0.0, time.monotonic() - started_clock),
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _resolve_target(self, request: RunRequest):
        if request.codespace is not None:
            if request.repository is not None:
                return self._workspace.resolve(
                    request.repository,
                    ref=request.ref,
                    name=request.codespace,
                )
            described = self._workspace.describe(request.codespace)
            if described.ok and request.ref is not None:
                target = described.workspace
                assert target is not None
                if target.ref is None:
                    return self._workspace._failure(
                        "workspace_ref_unknown",
                        "Cannot establish the selected workspace ref",
                        kind=FailureKind.SELECTION,
                    )
                if target.ref != request.ref:
                    return self._workspace._failure(
                        "workspace_ref_mismatch",
                        "Selected workspace does not match the requested ref",
                        kind=FailureKind.SELECTION,
                    )
            return described
        if request.repository is None:
            return self._workspace._failure(
                "workspace_target_required",
                "Either --codespace or --repo is required",
                kind=FailureKind.USAGE,
            )
        return self._workspace.resolve(request.repository, ref=request.ref)

    def execute(self, request: RunRequest) -> RunActionResult:
        run_id = str(uuid4())
        started_at = utc_now()
        started_clock = time.monotonic()
        if request.timeout_seconds <= 0:
            failure = DomainFailure(
                code="invalid_timeout",
                kind=FailureKind.USAGE,
                message="Timeout must be greater than zero",
            )
            return RunActionResult(
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                ),
                failure=failure,
            )
        if not request.argv or not request.argv[0]:
            failure = DomainFailure(
                code="remote_argv_required",
                kind=FailureKind.USAGE,
                message="A remote executable and arguments are required after --",
            )
            return RunActionResult(
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                ),
                failure=failure,
            )

        resolved = self._resolve_target(request)
        if not resolved.ok:
            assert resolved.failure is not None
            return RunActionResult(
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                ),
                failure=resolved.failure,
            )
        workspace = resolved.workspace
        assert workspace is not None
        outcome = self._transport.execute(
            workspace.name,
            request.argv,
            timeout_seconds=request.timeout_seconds,
        )
        if outcome.failure is not None:
            return RunActionResult(
                workspace=workspace,
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                ),
                failure=outcome.failure,
            )
        result = outcome.result
        assert result is not None
        if result.timed_out:
            failure = DomainFailure(
                code="remote_timeout",
                kind=FailureKind.REMOTE,
                message="Controller timeout expired before remote completion was observed",
            )
            return RunActionResult(
                workspace=workspace,
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                    timed_out=True,
                    remote_completion="unknown",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    stderr_mixed=True,
                ),
                failure=failure,
            )
        if result.returncode == 255:
            failure = DomainFailure(
                code="transport_failure",
                kind=FailureKind.INFRASTRUCTURE,
                message="Codespaces SSH transport failed or returned ambiguous status 255",
                retryable=True,
            )
            return RunActionResult(
                workspace=workspace,
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                    exit_code=255,
                    remote_completion="unknown",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    stderr_mixed=True,
                ),
                failure=failure,
            )
        assert result.returncode is not None
        if result.returncode != 0:
            failure = DomainFailure(
                code="remote_task_failed",
                kind=FailureKind.REMOTE,
                message="Remote task completed with a non-zero status",
            )
            return RunActionResult(
                workspace=workspace,
                record=self._record(
                    run_id=run_id,
                    request=request,
                    started_at=started_at,
                    started_clock=started_clock,
                    exit_code=result.returncode,
                    remote_completion="failed",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    stderr_mixed=True,
                ),
                failure=failure,
            )
        return RunActionResult(
            workspace=workspace,
            record=self._record(
                run_id=run_id,
                request=request,
                started_at=started_at,
                started_clock=started_clock,
                exit_code=0,
                remote_completion="success",
                stdout=result.stdout,
                stderr=result.stderr,
                stderr_mixed=True,
            ),
        )
