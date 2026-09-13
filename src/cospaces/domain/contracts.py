"""Shared machine-contract primitives."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class ExitStatus(IntEnum):
    SUCCESS = 0
    INTERNAL = 1
    USAGE = 2
    INFRASTRUCTURE = 3
    SELECTION = 4
    REMOTE = 5
    PERSISTENCE = 6
    VERIFICATION = 7


class FailureKind(StrEnum):
    USAGE = "usage"
    INFRASTRUCTURE = "infrastructure"
    SELECTION = "selection"
    REMOTE = "remote"
    PERSISTENCE = "persistence"
    VERIFICATION = "verification"
    INTERNAL = "internal"
    NOT_IMPLEMENTED = "not_implemented"


_FAILURE_STATUS: dict[FailureKind, ExitStatus] = {
    FailureKind.USAGE: ExitStatus.USAGE,
    FailureKind.INFRASTRUCTURE: ExitStatus.INFRASTRUCTURE,
    FailureKind.SELECTION: ExitStatus.SELECTION,
    FailureKind.REMOTE: ExitStatus.REMOTE,
    FailureKind.PERSISTENCE: ExitStatus.PERSISTENCE,
    FailureKind.VERIFICATION: ExitStatus.VERIFICATION,
    FailureKind.INTERNAL: ExitStatus.INTERNAL,
    FailureKind.NOT_IMPLEMENTED: ExitStatus.INTERNAL,
}


@dataclass(frozen=True)
class DomainFailure:
    code: str
    kind: FailureKind
    message: str
    retryable: bool = False

    @property
    def exit_status(self) -> ExitStatus:
        return _FAILURE_STATUS[self.kind]
