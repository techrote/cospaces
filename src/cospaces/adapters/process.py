"""Process adapter primitives."""

import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class ProcessAdapter:
    def capture(
        self,
        argv: tuple[str, ...],
        *,
        environment: Mapping[str, str] | None = None,
    ) -> CommandResult:
        process_environment = os.environ.copy()
        if environment is not None:
            process_environment.update(environment)
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            env=process_environment,
        )
        return CommandResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
