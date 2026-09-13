"""Structured remote-run domain records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RunRequest:
    argv: tuple[str, ...]
    codespace: str | None = None
    repository: str | None = None
    ref: str | None = None
    timeout_seconds: float = 600.0
    task_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    argv: tuple[str, ...]
    task_id: str | None
    correlation_id: str | None
    timeout_seconds: float
    exit_code: int | None
    timed_out: bool
    remote_completion: str
    transport: str
    stdout: str
    stderr: str
    stderr_mixed: bool
    duration_seconds: float
    started_at: str
    finished_at: str
