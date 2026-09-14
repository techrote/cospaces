"""T6 fixture execution composed from T2 run semantics."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.fixture import (
    FixtureAssertionResult,
    FixtureRunRecord,
    MetricValue,
)
from cospaces.domain.results import utc_now
from cospaces.domain.run import RunRequest
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.fixture_command import (
    FIXTURE_SETUP_EXIT_CODES,
    OUTPUT_CHECK_EXIT_CODES,
    build_fixture_argv,
    build_head_probe_argv,
    build_output_check_argv,
)
from cospaces.fixture_config import FixtureAssertion, FixtureDefinition, load_fixture
from cospaces.services.run_service import RunActionResult, RunService

_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


@dataclass(frozen=True)
class FixtureRequest:
    fixture: str
    repository: str | None = None
    ref: str | None = None
    codespace: str | None = None
    root: Path = Path(".")
    task_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class FixtureActionResult:
    record: FixtureRunRecord | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.record is not None and self.failure is None and self.record.passed


def _definition_digest(fixture: FixtureDefinition) -> str:
    encoded = json.dumps(
        fixture.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _failure(code: str, message: str, kind: FailureKind = FailureKind.VERIFICATION) -> DomainFailure:
    return DomainFailure(code=code, kind=kind, message=message)


def _setup_failure(result: RunActionResult) -> DomainFailure | None:
    exit_code = result.record.exit_code
    if exit_code not in FIXTURE_SETUP_EXIT_CODES:
        return None
    mapping = {
        96: ("fixture_input_missing", "A declared fixture input is missing"),
        97: ("fixture_environment_error", "The remote repository root is unavailable"),
        98: (
            "fixture_working_directory_missing",
            "The fixture working directory is unavailable",
        ),
        99: ("fixture_path_escape", "A fixture path escaped the repository root"),
    }
    code, message = mapping[exit_code]
    return _failure(code, message)


def _output_failure(result: RunActionResult) -> DomainFailure | None:
    exit_code = result.record.exit_code
    if exit_code not in OUTPUT_CHECK_EXIT_CODES:
        return None
    mapping = {
        94: ("fixture_environment_error", "The remote repository root is unavailable"),
        95: ("fixture_output_missing", "A declared fixture output is missing"),
        99: ("fixture_output_escape", "A declared fixture output escaped the repository root"),
    }
    code, message = mapping[exit_code]
    return _failure(code, message)


def _metric_scalar(value: object) -> MetricValue | object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return _INVALID


_INVALID = object()


def _parse_metrics(fixture: FixtureDefinition, stdout: str) -> tuple[dict[str, MetricValue], DomainFailure | None]:
    if fixture.metrics_format == "none":
        return {}, None
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        return {}, _failure("fixture_metrics_parse_failed", "Fixture emitted no metrics JSON line")
    try:
        raw = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {}, _failure(
            "fixture_metrics_parse_failed", "Fixture final non-empty stdout line is not JSON"
        )
    if not isinstance(raw, dict) or len(raw) > 256:
        return {}, _failure(
            "fixture_metrics_parse_failed", "Fixture metrics must be a bounded JSON object"
        )
    metrics: dict[str, MetricValue] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or len(key) > 128:
            return {}, _failure(
                "fixture_metrics_parse_failed", "Fixture metric names must be bounded strings"
            )
        parsed = _metric_scalar(value)
        if parsed is _INVALID:
            return {}, _failure(
                "fixture_metrics_parse_failed", "Fixture metric values must be finite scalars"
            )
        metrics[key] = parsed  # type: ignore[assignment]
    return metrics, None


def _compare(actual: MetricValue, operator: str, expected: MetricValue) -> tuple[bool, str | None]:
    if operator == "==":
        return actual == expected, None
    if operator == "!=":
        return actual != expected, None
    numeric = (
        isinstance(actual, int | float)
        and not isinstance(actual, bool)
        and isinstance(expected, int | float)
        and not isinstance(expected, bool)
    )
    if not numeric:
        return False, "incomparable_values"
    left = float(actual)
    right = float(expected)
    if operator == ">":
        return left > right, None
    if operator == ">=":
        return left >= right, None
    if operator == "<":
        return left < right, None
    if operator == "<=":
        return left <= right, None
    return False, "unsupported_operator"


def _evaluate_assertions(
    definitions: tuple[FixtureAssertion, ...], metrics: dict[str, MetricValue]
) -> tuple[FixtureAssertionResult, ...]:
    results: list[FixtureAssertionResult] = []
    for assertion in definitions:
        if assertion.metric not in metrics:
            results.append(
                FixtureAssertionResult(
                    metric=assertion.metric,
                    operator=assertion.operator,
                    expected=assertion.value,
                    actual=None,
                    passed=False,
                    reason="missing_metric",
                )
            )
            continue
        actual = metrics[assertion.metric]
        passed, reason = _compare(actual, assertion.operator, assertion.value)
        results.append(
            FixtureAssertionResult(
                metric=assertion.metric,
                operator=assertion.operator,
                expected=assertion.value,
                actual=actual,
                passed=passed,
                reason=reason,
            )
        )
    return tuple(results)


class FixtureService:
    def __init__(self, run: RunService | None = None) -> None:
        self._run = run or RunService()

    def _record(
        self,
        *,
        fixture_run_id: str,
        fixture: FixtureDefinition,
        definition_digest: str,
        task_run_id: str,
        support_run_ids: tuple[str, ...],
        workspace: WorkspaceIdentity,
        head: str | None,
        started_at: str,
        started_clock: float,
        metrics: dict[str, MetricValue] | None = None,
        assertions: tuple[FixtureAssertionResult, ...] = (),
        complete: bool,
        passed: bool,
        failure_code: str | None = None,
    ) -> FixtureRunRecord:
        return FixtureRunRecord(
            fixture_run_id=fixture_run_id,
            fixture=fixture.name,
            definition_digest=definition_digest,
            task_run_id=task_run_id,
            support_run_ids=support_run_ids,
            repository=workspace.repository,
            ref=workspace.ref,
            head=head,
            workspace=workspace,
            command=fixture.command,
            working_directory=fixture.working_directory,
            tags=fixture.tags,
            seed=fixture.seed,
            parameters=fixture.parameters,
            inputs=fixture.inputs,
            outputs=fixture.outputs,
            metrics_format=fixture.metrics_format,
            metrics=metrics or {},
            assertions=assertions,
            started_at=started_at,
            finished_at=utc_now(),
            duration_seconds=round(max(0.0, time.monotonic() - started_clock), 6),
            complete=complete,
            passed=passed,
            failure_code=failure_code,
        )

    def execute(self, request: FixtureRequest) -> FixtureActionResult:
        loaded = load_fixture(request.root, request.fixture)
        if not loaded.ok:
            return FixtureActionResult(failure=loaded.failure)
        fixture = loaded.fixture
        assert fixture is not None

        fixture_run_id = str(uuid4())
        digest = _definition_digest(fixture)
        started_at = utc_now()
        started_clock = time.monotonic()
        task = self._run.execute(
            RunRequest(
                argv=build_fixture_argv(fixture),
                repository=request.repository,
                ref=request.ref,
                codespace=request.codespace,
                timeout_seconds=fixture.timeout_seconds,
                task_id=request.task_id or f"fixture:{fixture.name}",
                correlation_id=request.correlation_id or fixture_run_id,
            )
        )
        workspace = task.workspace
        if workspace is None:
            return FixtureActionResult(failure=task.failure)
        if task.failure is not None:
            failure = _setup_failure(task)
            if failure is None:
                if task.failure.kind == FailureKind.REMOTE:
                    failure = _failure(
                        "fixture_task_failed",
                        "The fixture task did not complete successfully",
                        FailureKind.REMOTE,
                    )
                else:
                    failure = task.failure
            record = self._record(
                fixture_run_id=fixture_run_id,
                fixture=fixture,
                definition_digest=digest,
                task_run_id=task.record.run_id,
                support_run_ids=(),
                workspace=workspace,
                head=None,
                started_at=started_at,
                started_clock=started_clock,
                complete=False,
                passed=False,
                failure_code=failure.code,
            )
            return FixtureActionResult(record=record, failure=failure)

        support_run_ids: list[str] = []
        head_result = self._run.execute(
            RunRequest(
                argv=build_head_probe_argv(),
                repository=workspace.repository,
                ref=workspace.ref,
                codespace=workspace.name,
                timeout_seconds=30.0,
                task_id=request.task_id or f"fixture:{fixture.name}",
                correlation_id=fixture_run_id,
            )
        )
        support_run_ids.append(head_result.record.run_id)
        head = head_result.record.stdout.strip().splitlines()[0] if head_result.record.stdout.strip() else None
        if head_result.failure is not None or head is None or _SHA_RE.fullmatch(head) is None:
            failure = head_result.failure
            if failure is None or failure.kind == FailureKind.REMOTE:
                failure = _failure(
                    "fixture_provenance_failed",
                    "Could not establish the remote fixture Git HEAD",
                )
            record = self._record(
                fixture_run_id=fixture_run_id,
                fixture=fixture,
                definition_digest=digest,
                task_run_id=task.record.run_id,
                support_run_ids=tuple(support_run_ids),
                workspace=workspace,
                head=None,
                started_at=started_at,
                started_clock=started_clock,
                complete=False,
                passed=False,
                failure_code=failure.code,
            )
            return FixtureActionResult(record=record, failure=failure)

        if fixture.outputs:
            output_result = self._run.execute(
                RunRequest(
                    argv=build_output_check_argv(fixture.outputs),
                    repository=workspace.repository,
                    ref=workspace.ref,
                    codespace=workspace.name,
                    timeout_seconds=30.0,
                    task_id=request.task_id or f"fixture:{fixture.name}",
                    correlation_id=fixture_run_id,
                )
            )
            support_run_ids.append(output_result.record.run_id)
            if output_result.failure is not None:
                failure = _output_failure(output_result)
                if failure is None:
                    failure = output_result.failure
                    if failure.kind == FailureKind.REMOTE:
                        failure = _failure(
                            "fixture_output_check_failed",
                            "Could not validate declared fixture outputs",
                        )
                record = self._record(
                    fixture_run_id=fixture_run_id,
                    fixture=fixture,
                    definition_digest=digest,
                    task_run_id=task.record.run_id,
                    support_run_ids=tuple(support_run_ids),
                    workspace=workspace,
                    head=head,
                    started_at=started_at,
                    started_clock=started_clock,
                    complete=False,
                    passed=False,
                    failure_code=failure.code,
                )
                return FixtureActionResult(record=record, failure=failure)

        metrics, metrics_failure = _parse_metrics(fixture, task.record.stdout)
        if metrics_failure is not None:
            record = self._record(
                fixture_run_id=fixture_run_id,
                fixture=fixture,
                definition_digest=digest,
                task_run_id=task.record.run_id,
                support_run_ids=tuple(support_run_ids),
                workspace=workspace,
                head=head,
                started_at=started_at,
                started_clock=started_clock,
                complete=True,
                passed=False,
                failure_code=metrics_failure.code,
            )
            return FixtureActionResult(record=record, failure=metrics_failure)

        assertions = _evaluate_assertions(fixture.assertions, metrics)
        assertions_passed = all(item.passed for item in assertions)
        failure = None
        if not assertions_passed:
            failure = _failure(
                "fixture_assertion_failed",
                "One or more fixture assertions failed",
            )
        record = self._record(
            fixture_run_id=fixture_run_id,
            fixture=fixture,
            definition_digest=digest,
            task_run_id=task.record.run_id,
            support_run_ids=tuple(support_run_ids),
            workspace=workspace,
            head=head,
            started_at=started_at,
            started_clock=started_clock,
            metrics=metrics,
            assertions=assertions,
            complete=True,
            passed=assertions_passed,
            failure_code=failure.code if failure is not None else None,
        )
        return FixtureActionResult(record=record, failure=failure)
