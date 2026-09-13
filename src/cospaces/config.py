"""Repository-local configuration model and parser."""

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any

from .domain.contracts import DomainFailure, FailureKind


@dataclass(frozen=True)
class CospacesConfig:
    schema_version: int = 1
    extra_sections: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfigLoadResult:
    config: CospacesConfig | None
    failure: DomainFailure | None

    @property
    def ok(self) -> bool:
        return self.config is not None and self.failure is None


def _failure(code: str, message: str) -> ConfigLoadResult:
    return ConfigLoadResult(
        config=None,
        failure=DomainFailure(code=code, kind=FailureKind.USAGE, message=message),
    )


def load_config(path: str | Path = ".cospaces.toml") -> ConfigLoadResult:
    config_path = Path(path)
    if not config_path.exists():
        return ConfigLoadResult(config=CospacesConfig(), failure=None)

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return _failure("configuration_error", f"Invalid configuration: {exc}")

    control = data.get("cospaces", {})
    if not isinstance(control, dict):
        return _failure("configuration_error", "[cospaces] must be a table")

    unknown = sorted(set(control) - {"schema_version"})
    if unknown:
        return _failure("configuration_error", "Unknown [cospaces] key")

    schema_version = control.get("schema_version", 1)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        return _failure("configuration_error", "schema_version must be an integer")
    if schema_version != 1:
        return _failure("configuration_error", "Unsupported schema_version")

    extra_sections = {key: value for key, value in data.items() if key != "cospaces"}
    return ConfigLoadResult(
        config=CospacesConfig(schema_version=schema_version, extra_sections=extra_sections),
        failure=None,
    )
