"""GitHub CLI adapter module."""

from dataclasses import dataclass

from .process import CommandResult, ProcessAdapter


@dataclass(frozen=True)
class GitHubCommand:
    arguments: tuple[str, ...]

    @property
    def argv(self) -> tuple[str, ...]:
        return ("gh", *self.arguments)


class GitHubCliAdapter:
    def __init__(self, process: ProcessAdapter | None = None) -> None:
        self._process = process or ProcessAdapter()

    def prepare(self, arguments: tuple[str, ...]) -> GitHubCommand:
        return GitHubCommand(arguments=arguments)

    def capture(self, arguments: tuple[str, ...]) -> CommandResult:
        command = self.prepare(arguments)
        return self._process.capture(
            command.argv,
            environment={"GH_PROMPT_DISABLED": "1"},
        )
