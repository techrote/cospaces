"""Process adapter primitives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class ProcessAdapter:
    """Marker boundary for controller-side process adapters."""
