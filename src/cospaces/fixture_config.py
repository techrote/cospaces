"""Repository-controlled T6 fixture definitions."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .config import load_config
from .domain.contracts import DomainFailure, FailureKind
from .domain.fixture import MetricValue

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PARAM_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_ALLOWED_OPERATORS = frozenset({"==", "!=", ">", ">=", "<", "<="})
_ALLOWED_METRICS_FORMATS = frozenset({"none", "json-last-line"})
_MAX_ARGS = 128
_MAX_ARG_CHARS = 4096
_MAX_TIMEOUT = 86400.0
_MAX_PATHS = 128
_MAX_PARAMETERS = 64
_MAX_ASSERTIONS = 64


@dataclass(frozen=True)
class FixtureAssertion:
    metric: str
    operator: str
    value: MetricValue

    def to_dict(self) -> dict[str, object]:
        return {"metric": self.metric, "operator": self.operator, "value": self.value}


@dataclass(frozen=True)
class FixtureDefinition:
    name: str
    command: tuple[str, ...]
    timeout_seconds: float
    working_directory: str
    tags: tuple[str, ...]
    seed: str | int | None
    parameters: dict[str, MetricValue]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    metrics_format: str
    assertions: tuple[FixtureAssertion, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "command": list(self.command),
            "timeout_seconds": self.timeout_seconds,
            "working_directory": self.working_directory,
            "tags": list(self.tags),
            "seed": self.seed,
            "parameters": dict(sorted(self.parameters.items())),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "metrics_format": self.metrics_format,
            "assertions": [item.to_dict() for item in self.assertions],
        }


@dataclass(frozen=True)
class FixtureConfigResult:
    fixture: FixtureDefinition | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.fixture is not None and self.failure is None


def _failure(code: str, message: str) -> FixtureConfigResult:
    return FixtureConfigResult(
        failure=DomainFailure(code=code, kind=FailureKind.USAGE, message=message)
    )


def _scalar(value: Any) -> MetricValue | object:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return _INVALID


_INVALID = object()


def _safe_relative_path(value: Any, field: str) -> str | DomainFailure:
    if not isinstance(value, str) or not value or len(value) > 512 or "\x00" in value:
        return DomainFailure(
            code="invalid_fixture",
            kind=FailureKind.USAGE,
            message=f"{field} must be a bounded repository-relative POSIX path",
        )
    if "\\" in value:
        return DomainFailure(
            code="invalid_fixture",
            kind=FailureKind.USAGE,
            message=f"{field} must use POSIX path separators",
        )
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return DomainFailure(
            code="invalid_fixture",
            kind=FailureKind.USAGE,
            message=f"{field} must remain within the repository",
        )
    return value


def _parse_paths(value: Any, field: str) -> tuple[str, ...] | DomainFailure:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > _MAX_PATHS:
        return DomainFailure(
            code="invalid_fixture",
            kind=FailureKind.USAGE,
            message=f"{field} must be a list of at most {_MAX_PATHS} paths",
        )
    result: list[str] = []
    for index, raw in enumerate(value):
        parsed = _safe_relative_path(raw, f"{field}[{index}]")
        if isinstance(parsed, DomainFailure):
            return parsed
        result.append(parsed)
    return tuple(result)


def _parse_parameters(value: Any) -> dict[str, MetricValue] | DomainFailure:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > _MAX_PARAMETERS:
        return DomainFailure(
            code="invalid_fixture",
            kind=FailureKind.USAGE,
            message=f"parameters must be a table with at most {_MAX_PARAMETERS} entries",
        )
    result: dict[str, MetricValue] = {}
    for name, raw in value.items():
        if not isinstance(name, str) or _PARAM_RE.fullmatch(name) is None:
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message="fixture parameter names must be bounded environment-safe identifiers",
            )
        parsed = _scalar(raw)
        if parsed is _INVALID:
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message=f"fixture parameter {name} must be a finite scalar",
            )
        result[name] = parsed  # type: ignore[assignment]
    return result


def _parse_assertions(value: Any) -> tuple[FixtureAssertion, ...] | DomainFailure:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > _MAX_ASSERTIONS:
        return DomainFailure(
            code="invalid_fixture",
            kind=FailureKind.USAGE,
            message=f"assertions must be a list of at most {_MAX_ASSERTIONS} tables",
        )
    result: list[FixtureAssertion] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message=f"assertions[{index}] must be a table",
            )
        unknown = sorted(set(raw) - {"metric", "operator", "value"})
        if unknown:
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message=f"assertions[{index}] contains unsupported keys: {', '.join(unknown)}",
            )
        metric = raw.get("metric")
        operator = raw.get("operator")
        expected = _scalar(raw.get("value"))
        if not isinstance(metric, str) or _NAME_RE.fullmatch(metric) is None:
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message=f"assertions[{index}].metric must be a bounded identifier",
            )
        if operator not in _ALLOWED_OPERATORS:
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message=f"assertions[{index}].operator is unsupported",
            )
        if expected is _INVALID:
            return DomainFailure(
                code="invalid_fixture",
                kind=FailureKind.USAGE,
                message=f"assertions[{index}].value must be a finite scalar",
            )
        result.append(FixtureAssertion(metric, operator, expected))  # type: ignore[arg-type]
    return tuple(result)


def load_fixture(root: str | Path, name: str) -> FixtureConfigResult:
    if _NAME_RE.fullmatch(name) is None:
        return _failure("invalid_fixture_name", "fixture name must be a bounded identifier")
    loaded = load_config(Path(root) / ".cospaces.toml")
    if not loaded.ok:
        return FixtureConfigResult(failure=loaded.failure)
    assert loaded.config is not None
    section = loaded.config.extra_sections.get("fixture")
    if not isinstance(section, dict) or name not in section:
        return _failure("fixture_not_found", f"fixture plan not found: {name}")
    raw = section[name]
    if not isinstance(raw, dict):
        return _failure("invalid_fixture", f"fixture.{name} must be a table")
    allowed = {
        "command",
        "timeout_seconds",
        "working_directory",
        "tags",
        "seed",
        "parameters",
        "inputs",
        "outputs",
        "metrics_format",
        "assertions",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        return _failure(
            "invalid_fixture", f"fixture.{name} contains unsupported keys: {', '.join(unknown)}"
        )
    command = raw.get("command")
    if (
        not isinstance(command, list)
        or not command
        or len(command) > _MAX_ARGS
        or not all(isinstance(item, str) for item in command)
        or not command[0]
        or any("\x00" in item or len(item) > _MAX_ARG_CHARS for item in command)
    ):
        return _failure("invalid_fixture", "fixture command must be a bounded non-empty argv list")
    timeout = raw.get("timeout_seconds", 600.0)
    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        return _failure("invalid_fixture", "fixture timeout_seconds must be numeric")
    timeout = float(timeout)
    if not math.isfinite(timeout) or not 0 < timeout <= _MAX_TIMEOUT:
        return _failure("invalid_fixture", "fixture timeout_seconds must be finite and positive")
    working = _safe_relative_path(raw.get("working_directory", "."), "working_directory")
    if isinstance(working, DomainFailure):
        return FixtureConfigResult(failure=working)
    tags_raw = raw.get("tags", [])
    if (
        not isinstance(tags_raw, list)
        or len(tags_raw) > 64
        or not all(isinstance(item, str) and _NAME_RE.fullmatch(item) for item in tags_raw)
    ):
        return _failure("invalid_fixture", "fixture tags must be bounded identifiers")
    seed_raw = raw.get("seed")
    if seed_raw is not None and (isinstance(seed_raw, bool) or not isinstance(seed_raw, str | int)):
        return _failure("invalid_fixture", "fixture seed must be a string or integer")
    parameters = _parse_parameters(raw.get("parameters"))
    if isinstance(parameters, DomainFailure):
        return FixtureConfigResult(failure=parameters)
    inputs = _parse_paths(raw.get("inputs"), "inputs")
    if isinstance(inputs, DomainFailure):
        return FixtureConfigResult(failure=inputs)
    outputs = _parse_paths(raw.get("outputs"), "outputs")
    if isinstance(outputs, DomainFailure):
        return FixtureConfigResult(failure=outputs)
    metrics_format = raw.get("metrics_format", "none")
    if metrics_format not in _ALLOWED_METRICS_FORMATS:
        return _failure(
            "invalid_fixture",
            f"metrics_format must be one of: {', '.join(sorted(_ALLOWED_METRICS_FORMATS))}",
        )
    assertions = _parse_assertions(raw.get("assertions"))
    if isinstance(assertions, DomainFailure):
        return FixtureConfigResult(failure=assertions)
    if assertions and metrics_format == "none":
        return _failure("invalid_fixture", "fixture assertions require a metrics_format")
    return FixtureConfigResult(
        fixture=FixtureDefinition(
            name=name,
            command=tuple(command),
            timeout_seconds=timeout,
            working_directory=working,
            tags=tuple(tags_raw),
            seed=seed_raw,
            parameters=parameters,
            inputs=inputs,
            outputs=outputs,
            metrics_format=metrics_format,
            assertions=assertions,
        )
    )
