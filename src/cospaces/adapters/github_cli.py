"""GitHub CLI adapter module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubCommand:
    arguments: tuple[str, ...]

    @property
    def argv(self) -> tuple[str, ...]:
        return ("gh", *self.arguments)


class GitHubCliAdapter:
    def prepare(self, arguments: tuple[str, ...]) -> GitHubCommand:
        return GitHubCommand(arguments=arguments)
