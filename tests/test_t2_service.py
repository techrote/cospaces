from uuid import UUID

from cospaces.adapters.process import CommandResult
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRequest
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.run_service import RunService
from cospaces.services.run_transport import TransportOutcome
from cospaces.services.workspace_service import WorkspaceActionResult


def identity(name: str = "space-one") -> WorkspaceIdentity:
    return WorkspaceIdentity(
        name=name,
        repository="owner/repo",
        ref="main",
        state="available",
        display_name=name,
        machine="standard",
    )


class FakeWorkspace:
    def __init__(self, outcome: WorkspaceActionResult) -> None:
        self.outcome = outcome
        self.calls: list[tuple[object, ...]] = []

    def describe(self, name: str) -> WorkspaceActionResult:
        self.calls.append(("describe", name))
        return self.outcome

    def resolve(
        self,
        repository: str,
        *,
        ref: str | None = None,
        name: str | None = None,
    ) -> WorkspaceActionResult:
        self.calls.append(("resolve", repository, ref, name))
        return self.outcome


class FakeTransport:
    def __init__(self, outcome: TransportOutcome) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, tuple[str, ...], float]] = []

    def execute(
        self,
        codespace: str,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> TransportOutcome:
        self.calls.append((codespace, argv, timeout_seconds))
        return self.outcome


def process_result(
    returncode: int | None,
    *,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
) -> CommandResult:
    return CommandResult(
        argv=("gh",),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )
