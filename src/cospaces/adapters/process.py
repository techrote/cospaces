"""Process adapter primitives."""

import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


class ProcessAdapter:
    def capture(
        self,
        argv: tuple[str, ...],
        *,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        process_environment = os.environ.copy()
        if environment is not None:
            process_environment.update(environment)
        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                env=process_environment,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                argv=argv,
                returncode=None,
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
                timed_out=True,
            )
        return CommandResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
