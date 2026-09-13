"""Structured remote-run domain records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RunRequest:
    argv: tuple[str, ...]
    codespace: str | None = None
    repository: str | None = None
    ref: str | None = None
