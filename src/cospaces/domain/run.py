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
