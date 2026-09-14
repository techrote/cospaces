"""T6 fixture result domain model."""

from dataclasses import dataclass
from typing import TypeAlias

from .workspace import WorkspaceIdentity

SCHEMA = "cospaces.fixture/v1"
MetricValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True)
class FixtureAssertionResult:
    metric: str
    operator: str
    expected: MetricValue
    actual: MetricValue
    passed: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric,
            "operator": self.operator,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FixtureRunRecord:
    fixture_run_id: str
    fixture: str
    definition_digest: str
    task_run_id: str
    support_run_ids: tuple[str, ...]
    repository: str | None
    ref: str | None
    head: str | None
    workspace: WorkspaceIdentity
    command: tuple[str, ...]
    working_directory: str
    tags: tuple[str, ...]
    seed: str | int | None
    parameters: dict[str, MetricValue]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    metrics_format: str
    metrics: dict[str, MetricValue]
    assertions: tuple[FixtureAssertionResult, ...]
    started_at: str
    finished_at: str
    duration_seconds: float
    complete: bool
    passed: bool
    failure_code: str | None = None
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "fixture_run_id": self.fixture_run_id,
            "fixture": self.fixture,
            "definition_digest": self.definition_digest,
            "task_run_id": self.task_run_id,
            "support_run_ids": list(self.support_run_ids),
            "repository": self.repository,
            "ref": self.ref,
            "head": self.head,
            "workspace": self.workspace.to_dict(),
            "command": list(self.command),
            "working_directory": self.working_directory,
            "tags": list(self.tags),
            "seed": self.seed,
            "parameters": dict(sorted(self.parameters.items())),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "metrics_format": self.metrics_format,
            "metrics": dict(sorted(self.metrics.items())),
            "assertions": [item.to_dict() for item in self.assertions],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "complete": self.complete,
            "passed": self.passed,
            "failure_code": self.failure_code,
        }
