"""Repository-declared verification domain records."""

from collections.abc import Mapping
from dataclasses import dataclass

SCHEMA = "cospaces.verify/v1"


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    command: tuple[str, ...]
    timeout_seconds: float
    required: bool = True
    working_directory: str | None = None
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class VerificationPlan:
    name: str
    checks: tuple[VerificationCheck, ...]


@dataclass(frozen=True)
class VerificationCheckRecord:
    name: str
    required: bool
    passed: bool
    timed_out: bool
    run_id: str
    exit_code: int | None
    remote_completion: str
    duration_ms: int
    failure_code: str | None
    command: tuple[str, ...]
    working_directory: str | None
    environment_keys: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "required": self.required,
            "passed": self.passed,
            "timed_out": self.timed_out,
            "run_id": self.run_id,
            "exit_code": self.exit_code,
            "remote_completion": self.remote_completion,
            "duration_ms": self.duration_ms,
            "failure_code": self.failure_code,
            "command": list(self.command),
            "working_directory": self.working_directory,
            "environment_keys": list(self.environment_keys),
        }


@dataclass(frozen=True)
class VerificationRecord:
    verification_id: str
    plan: str
    task_id: str | None
    correlation_id: str | None
    repository: str | None
    ref: str | None
    head: str | None
    workspace: Mapping[str, object] | None
    started_at: str
    finished_at: str
    complete: bool
    passed: bool
    checks: tuple[VerificationCheckRecord, ...]
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "verification_id": self.verification_id,
            "plan": self.plan,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "repository": self.repository,
            "ref": self.ref,
            "head": self.head,
            "workspace": dict(self.workspace) if self.workspace is not None else None,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "complete": self.complete,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }
