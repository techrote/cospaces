"""Safe bounded local repository context capture for checkpoints."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from cospaces.domain.checkpoint import WorkingTreeState
from cospaces.domain.contracts import DomainFailure, FailureKind

_CONFLICT_CODES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}


@dataclass(frozen=True)
class RepositoryContext:
    repository: str | None
    ref: str | None
    head: str | None
    working_tree: WorkingTreeState


@dataclass(frozen=True)
class RepositoryProbeResult:
    context: RepositoryContext | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


def _github_repository(remote: str) -> str | None:
    value = remote.strip()
    if value.startswith("git@github.com:"):
        path = value.removeprefix("git@github.com:")
    else:
        parsed = urlparse(value)
        if parsed.hostname != "github.com":
            return None
        path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    if len(parts) != 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def summarize_porcelain(text: str) -> WorkingTreeState:
    counts = {
        "modified": 0,
        "added": 0,
        "deleted": 0,
        "renamed": 0,
        "untracked": 0,
        "conflicted": 0,
    }
    lines = [line for line in text.splitlines() if line]
    for line in lines:
        code = line[:2] if len(line) >= 2 else ""
        if code == "??":
            counts["untracked"] += 1
        elif code in _CONFLICT_CODES:
            counts["conflicted"] += 1
        elif "R" in code:
            counts["renamed"] += 1
        elif "D" in code:
            counts["deleted"] += 1
        elif "A" in code:
            counts["added"] += 1
        else:
            counts["modified"] += 1
    summary = ";".join(f"{name}={value}" for name, value in counts.items())
    return WorkingTreeState(dirty=bool(lines), summary=summary)


class RepositoryProbe:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", *arguments),
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )

    def capture(self) -> RepositoryProbeResult:
        try:
            inside = self._git("rev-parse", "--is-inside-work-tree")
        except OSError:
            return RepositoryProbeResult(
                failure=DomainFailure(
                    code="git_unavailable",
                    kind=FailureKind.INFRASTRUCTURE,
                    message="Git is unavailable for repository context capture",
                )
            )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return RepositoryProbeResult(
                failure=DomainFailure(
                    code="repository_context_unavailable",
                    kind=FailureKind.INFRASTRUCTURE,
                    message="Checkpoint root is not inside a Git working tree",
                )
            )

        head_result = self._git("rev-parse", "HEAD")
        if head_result.returncode != 0:
            return RepositoryProbeResult(
                failure=DomainFailure(
                    code="repository_head_unavailable",
                    kind=FailureKind.INFRASTRUCTURE,
                    message="Git HEAD could not be established",
                )
            )
        ref_result = self._git("symbolic-ref", "--quiet", "--short", "HEAD")
        ref = ref_result.stdout.strip() if ref_result.returncode == 0 else None

        remote_result = self._git("remote", "get-url", "origin")
        repository = None
        if remote_result.returncode == 0:
            repository = _github_repository(remote_result.stdout)

        status_result = self._git("status", "--porcelain=v1", "--untracked-files=normal")
        if status_result.returncode != 0:
            return RepositoryProbeResult(
                failure=DomainFailure(
                    code="working_tree_status_unavailable",
                    kind=FailureKind.INFRASTRUCTURE,
                    message="Git working-tree state could not be established",
                )
            )
        return RepositoryProbeResult(
            context=RepositoryContext(
                repository=repository,
                ref=ref,
                head=head_result.stdout.strip(),
                working_tree=summarize_porcelain(status_result.stdout),
            )
        )
