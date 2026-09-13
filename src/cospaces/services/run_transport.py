"""Codespaces SSH transport primitives."""

import re
import shlex
from dataclasses import dataclass

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.domain.contracts import DomainFailure, FailureKind

TRANSPORT_NAME = "gh-codespace-ssh"
_MIN_GH_VERSION = (2, 62, 0)
_VERSION_RE = re.compile(r"gh version (\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class TransportOutcome:
    result: CommandResult | None = None
    failure: DomainFailure | None = None


def encode_remote_argv(argv: tuple[str, ...]) -> str:
    if not argv or not argv[0]:
        raise ValueError("remote argv must contain a non-empty executable")
    if any("\x00" in item for item in argv):
        raise ValueError("remote argv cannot contain NUL characters")
    return f"set -- {shlex.join(argv)}; \"$@\""


def parse_gh_version(text: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(text)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


class CodespaceSshTransport:
    def __init__(self, github: GitHubCliAdapter | None = None) -> None:
        self._github = github or GitHubCliAdapter()

    def _preflight(self) -> DomainFailure | None:
        try:
            result = self._github.capture(("--version",), timeout_seconds=10.0)
        except OSError:
            return DomainFailure(
                code="github_cli_unavailable",
                kind=FailureKind.INFRASTRUCTURE,
                message="GitHub CLI is unavailable",
            )
        if result.timed_out or result.returncode != 0:
            return DomainFailure(
                code="github_cli_version_unavailable",
                kind=FailureKind.INFRASTRUCTURE,
                message="GitHub CLI version could not be established",
            )
        version = parse_gh_version(result.stdout)
        if version is None:
            return DomainFailure(
                code="github_cli_version_unknown",
                kind=FailureKind.INFRASTRUCTURE,
                message="GitHub CLI returned an unrecognised version",
            )
        if version < _MIN_GH_VERSION:
            return DomainFailure(
                code="unsafe_github_cli_version",
                kind=FailureKind.INFRASTRUCTURE,
                message="GitHub CLI 2.62.0 or newer is required for Codespaces SSH",
            )
        return None

    def execute(
        self,
        codespace: str,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> TransportOutcome:
        failure = self._preflight()
        if failure is not None:
            return TransportOutcome(failure=failure)
        try:
            encoded = encode_remote_argv(argv)
        except ValueError as exc:
            return TransportOutcome(
                failure=DomainFailure(
                    code="invalid_remote_argv",
                    kind=FailureKind.USAGE,
                    message=str(exc),
                )
            )
        try:
            result = self._github.capture(
                (
                    "codespace",
                    "ssh",
                    "--codespace",
                    codespace,
                    "--",
                    encoded,
                ),
                timeout_seconds=timeout_seconds,
            )
        except OSError:
            return TransportOutcome(
                failure=DomainFailure(
                    code="github_cli_unavailable",
                    kind=FailureKind.INFRASTRUCTURE,
                    message="GitHub CLI is unavailable",
                )
            )
        return TransportOutcome(result=result)
