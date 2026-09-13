"""Machine-readable result envelope helpers."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any

from .contracts import DomainFailure

SCHEMA = "cospaces.result/v1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ResultEnvelope:
    operation: str
    ok: bool
    started_at: str
    finished_at: str
    workspace: Mapping[str, Any] | None = None
    result: Mapping[str, Any] | None = None
    error: DomainFailure | None = None
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        error_payload: dict[str, Any] | None = None
        if self.error is not None:
            error_payload = {
                "code": self.error.code,
                "kind": self.error.kind.value,
                "message": self.error.message,
                "retryable": self.error.retryable,
            }
        return {
            "schema": self.schema,
            "operation": self.operation,
            "ok": self.ok,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "workspace": dict(self.workspace) if self.workspace is not None else None,
            "result": dict(self.result) if self.result is not None else None,
            "error": error_payload,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def success_result(
    operation: str,
    *,
    result: Mapping[str, Any] | None = None,
    workspace: Mapping[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> ResultEnvelope:
    return ResultEnvelope(
        operation=operation,
        ok=True,
        started_at=started_at or utc_now(),
        finished_at=finished_at or utc_now(),
        workspace=workspace,
        result=result,
    )


def failure_result(
    operation: str,
    failure: DomainFailure,
    *,
    workspace: Mapping[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> ResultEnvelope:
    return ResultEnvelope(
        operation=operation,
        ok=False,
        started_at=started_at or utc_now(),
        finished_at=finished_at or utc_now(),
        workspace=workspace,
        error=failure,
    )
