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

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "command": list(self.argv),
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "timeout_seconds": self.timeout_seconds,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "remote_completion": self.remote_completion,
            "transport": self.transport,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stderr_mixed": self.stderr_mixed,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
