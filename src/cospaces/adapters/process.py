"""Process adapter primitives."""

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class ProcessAdapter:
    def capture(self, argv: tuple[str, ...]) -> CommandResult:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        return CommandResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
