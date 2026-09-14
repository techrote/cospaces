"""T5 capability-report domain model."""

from dataclasses import dataclass
from enum import StrEnum

from .workspace import WorkspaceIdentity

SCHEMA = "cospaces.capabilities/v1"


class CapabilityState(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapabilityObservation:
    name: str
    state: CapabilityState
    value: str | None = None
    version: str | None = None
    reason: str | None = None
    run_id: str | None = None
    command: tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "value": self.value,
            "version": self.version,
            "reason": self.reason,
            "run_id": self.run_id,
            "command": list(self.command) if self.command is not None else None,
        }


@dataclass(frozen=True)
class CapabilityReport:
    controller_version: str
    github_cli: CapabilityObservation
    workspace: WorkspaceIdentity
    declared_support: dict[str, bool]
    observations: tuple[CapabilityObservation, ...]
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "controller": {
                "cospaces_version": self.controller_version,
                "github_cli": self.github_cli.to_dict(),
            },
            "workspace": self.workspace.to_dict(),
            "declared_support": dict(sorted(self.declared_support.items())),
            "observations": [item.to_dict() for item in self.observations],
        }
