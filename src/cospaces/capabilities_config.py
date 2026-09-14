"""Repository-declared T5 capability probes."""

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import load_config
from .domain.contracts import DomainFailure, FailureKind

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_PROBES = 64
_MAX_ARGS = 128
_MAX_ARG_CHARS = 4096
_MAX_TIMEOUT = 300.0


@dataclass(frozen=True)
class CapabilityProbe:
    name: str
    command: tuple[str, ...]
    timeout_seconds: float = 10.0
    version_regex: str | None = None


@dataclass(frozen=True)
class CapabilityConfig:
    declared_support: dict[str, bool]
    probes: tuple[CapabilityProbe, ...]


@dataclass(frozen=True)
class CapabilityConfigResult:
    config: CapabilityConfig | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.config is not None and self.failure is None


def _failure(message: str) -> CapabilityConfigResult:
    return CapabilityConfigResult(
        failure=DomainFailure(
            code="capabilities_configuration_error",
            kind=FailureKind.USAGE,
            message=message,
        )
    )


def _parse_support(value: Any) -> dict[str, bool] | str:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return "[capabilities.supports] must be a table"
    result: dict[str, bool] = {}
    for name, supported in value.items():
        if not isinstance(name, str) or _NAME_RE.fullmatch(name) is None:
            return "capability support names must be bounded identifiers"
        if not isinstance(supported, bool):
            return f"capabilities.supports.{name} must be a boolean"
        result[name] = supported
    return result


def _parse_probe(raw: Any, index: int) -> CapabilityProbe | str:
    if not isinstance(raw, dict):
        return f"capabilities.probes[{index}] must be a table"
    unknown = sorted(set(raw) - {"name", "command", "timeout_seconds", "version_regex"})
    if unknown:
        return f"capabilities.probes[{index}] contains unsupported keys: {', '.join(unknown)}"
    name = raw.get("name")
    if not isinstance(name, str) or _NAME_RE.fullmatch(name) is None:
        return f"capabilities.probes[{index}].name must be a bounded identifier"
    command = raw.get("command")
    if (
        not isinstance(command, list)
        or not command
        or len(command) > _MAX_ARGS
        or not all(isinstance(item, str) for item in command)
    ):
        return f"capabilities.probes[{index}].command must be a non-empty string argv list"
    if not command[0]:
        return f"capabilities.probes[{index}].command executable cannot be empty"
    if any("\x00" in item or len(item) > _MAX_ARG_CHARS for item in command):
        return f"capabilities.probes[{index}].command contains an invalid argument"
    timeout = raw.get("timeout_seconds", 10.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        return f"capabilities.probes[{index}].timeout_seconds must be numeric"
    timeout = float(timeout)
    if not math.isfinite(timeout) or not 0 < timeout <= _MAX_TIMEOUT:
        return f"capabilities.probes[{index}].timeout_seconds must be finite and within (0, 300]"
    version_regex = raw.get("version_regex")
    if version_regex is not None:
        if not isinstance(version_regex, str) or not version_regex or len(version_regex) > 512:
            return f"capabilities.probes[{index}].version_regex must be a bounded string"
        try:
            re.compile(version_regex)
        except re.error:
            return f"capabilities.probes[{index}].version_regex is invalid"
    return CapabilityProbe(
        name=name,
        command=tuple(command),
        timeout_seconds=timeout,
        version_regex=version_regex,
    )


def load_capability_config(root: str | Path = ".") -> CapabilityConfigResult:
    root_path = Path(root)
    loaded = load_config(root_path / ".cospaces.toml")
    if not loaded.ok:
        return CapabilityConfigResult(failure=loaded.failure)
    assert loaded.config is not None
    raw = loaded.config.extra_sections.get("capabilities")
    if raw is None:
        return CapabilityConfigResult(config=CapabilityConfig({}, ()))
    if not isinstance(raw, dict):
        return _failure("[capabilities] must be a table")
    unknown = sorted(set(raw) - {"supports", "probes"})
    if unknown:
        return _failure(f"[capabilities] contains unsupported keys: {', '.join(unknown)}")
    support = _parse_support(raw.get("supports"))
    if isinstance(support, str):
        return _failure(support)
    probes_raw = raw.get("probes", [])
    if not isinstance(probes_raw, list) or len(probes_raw) > _MAX_PROBES:
        return _failure(f"capabilities.probes must be a list of at most {_MAX_PROBES} tables")
    probes: list[CapabilityProbe] = []
    names: set[str] = set()
    for index, item in enumerate(probes_raw):
        parsed = _parse_probe(item, index)
        if isinstance(parsed, str):
            return _failure(parsed)
        if parsed.name in names:
            return _failure(f"duplicate capability probe name: {parsed.name}")
        names.add(parsed.name)
        probes.append(parsed)
    return CapabilityConfigResult(config=CapabilityConfig(support, tuple(probes)))
