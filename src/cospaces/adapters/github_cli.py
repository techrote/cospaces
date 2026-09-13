"""GitHub CLI adapter module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubCommand:
    arguments: tuple[str, ...]
