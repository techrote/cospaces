"""Repository-local configuration model."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CospacesConfig:
    schema_version: int = 1
    extra_sections: dict[str, Any] = field(default_factory=dict)
