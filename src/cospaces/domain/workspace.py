"""Normalized Codespaces workspace identity."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkspaceIdentity:
    name: str
    repository: str | None
    ref: str | None
    state: str
    display_name: str | None
    machine: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "name": self.name,
            "repository": self.repository,
            "ref": self.ref,
            "state": self.state,
            "display_name": self.display_name,
            "machine": self.machine,
        }


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _repository(value: Any) -> str | None:
    if isinstance(value, str):
        return value or None
    if not isinstance(value, Mapping):
        return None
    for key in ("nameWithOwner", "fullName", "nwo"):
        candidate = _string(value.get(key))
        if candidate is not None:
            return candidate
    name = _string(value.get("name"))
    owner_value = value.get("owner")
    owner: str | None = None
    if isinstance(owner_value, str):
        owner = owner_value or None
    elif isinstance(owner_value, Mapping):
        owner = _string(owner_value.get("login")) or _string(owner_value.get("name"))
    if owner is not None and name is not None:
        return f"{owner}/{name}"
    return None


def _ref(payload: Mapping[str, Any]) -> str | None:
    git_status = payload.get("gitStatus")
    if isinstance(git_status, Mapping):
        return _string(git_status.get("ref"))
    return None


def _state(value: Any) -> str:
    raw = _string(value)
    if raw is None:
        return "unknown"
    normalized = raw.casefold()
    if normalized in {"available", "running"}:
        return "available"
    if normalized in {"shutdown", "stopped"}:
        return "shutdown"
    if normalized in {"starting", "creating", "rebuilding"}:
        return "starting"
    return "unknown"


def workspace_from_payload(payload: Mapping[str, Any]) -> WorkspaceIdentity | None:
    name = _string(payload.get("name"))
    if name is None:
        return None
    return WorkspaceIdentity(
        name=name,
        repository=_repository(payload.get("repository")),
        ref=_ref(payload),
        state=_state(payload.get("state")),
        display_name=_string(payload.get("displayName")),
        machine=_string(payload.get("machineName")),
    )
