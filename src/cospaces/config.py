"""Repository-local configuration model."""

from dataclasses import dataclass, field
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
