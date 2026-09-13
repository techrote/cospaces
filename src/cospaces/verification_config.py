"""Strict verification-plan parsing from repository configuration."""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from cospaces.config import load_config
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.verification import VerificationCheck, VerificationPlan

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_CHECKS = 64
_MAX_ARGS = 128
_MAX_ARG_CHARS = 4096
_MAX_ENV = 64
_MAX_WORKDIR_CHARS = 256


@dataclass(frozen=True)
class VerificationPlanLoadResult:
    plan: VerificationPlan | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.plan is not None and self.failure is None


def _failure(code: str, message: str) -> VerificationPlanLoadResult:
    return VerificationPlanLoadResult(
        failure=DomainFailure(code=code, kind=FailureKind.USAGE, message=message)
    )


def _text(value: Any, label: str, *, limit: int = _MAX_ARG_CHARS) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise ValueError(f"{label} exceeds {limit} characters")
    if "\x00" in value:
        raise ValueError(f"{label} cannot contain NUL characters")
    return value


def _working_directory(value: Any) -> str | None:
    if value is None:
        return None
    text = _text(value, "working_directory", limit=_MAX_WORKDIR_CHARS)
    if "\\" in text:
        raise ValueError("working_directory must use POSIX separators")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("working_directory must remain repository-relative")
    normalized = path.as_posix()
    return "." if normalized in {"", "."} else normalized


def _environment(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise ValueError("environment must be a table")
    if len(value) > _MAX_ENV:
        raise ValueError(f"environment exceeds {_MAX_ENV} entries")
    result: list[tuple[str, str]] = []
    for raw_key, raw_value in sorted(value.items()):
        if not isinstance(raw_key, str) or _ENV_RE.fullmatch(raw_key) is None:
            raise ValueError("environment keys must be POSIX variable names")
        item = _text(raw_value, f"environment.{raw_key}")
        result.append((raw_key, item))
    return tuple(result)


def _check(payload: Any, index: int) -> VerificationCheck:
    if not isinstance(payload, dict):
        raise ValueError(f"checks[{index}] must be a table")
    allowed = {
        "name",
        "command",
        "timeout_seconds",
        "required",
        "working_directory",
        "environment",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"checks[{index}] contains unknown keys: {unknown}")

    name = _text(payload.get("name"), f"checks[{index}].name", limit=64)
    if _NAME_RE.fullmatch(name) is None:
        raise ValueError(f"checks[{index}].name has invalid characters")

    raw_command = payload.get("command")
    if not isinstance(raw_command, list) or not raw_command:
        raise ValueError(f"checks[{index}].command must be a non-empty array")
    if len(raw_command) > _MAX_ARGS:
        raise ValueError(f"checks[{index}].command exceeds {_MAX_ARGS} arguments")
    command = tuple(
        _text(item, f"checks[{index}].command item") for item in raw_command
    )

    raw_timeout = payload.get("timeout_seconds", 600)
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
        raise ValueError(f"checks[{index}].timeout_seconds must be numeric")
    timeout = float(raw_timeout)
    if timeout <= 0 or timeout > 86400:
        raise ValueError(f"checks[{index}].timeout_seconds must be within (0, 86400]")

    required = payload.get("required", True)
    if not isinstance(required, bool):
        raise ValueError(f"checks[{index}].required must be boolean")

    return VerificationCheck(
        name=name,
        command=command,
        timeout_seconds=timeout,
        required=required,
        working_directory=_working_directory(payload.get("working_directory")),
        environment=_environment(payload.get("environment")),
    )


def load_verification_plan(root: Path, plan_name: str) -> VerificationPlanLoadResult:
    if _NAME_RE.fullmatch(plan_name) is None:
        return _failure("invalid_verification_plan", "Verification plan name is invalid")

    loaded = load_config(root / ".cospaces.toml")
    if not loaded.ok:
        assert loaded.failure is not None
        return VerificationPlanLoadResult(failure=loaded.failure)
    assert loaded.config is not None

    verify = loaded.config.extra_sections.get("verify")
    if verify is None:
        return _failure(
            "verification_config_missing",
            "Repository configuration does not declare a [verify] section",
        )
    if not isinstance(verify, dict):
        return _failure("verification_configuration_error", "[verify] must be a table")
    raw_plan = verify.get(plan_name)
    if raw_plan is None:
        return _failure(
            "verification_plan_not_found",
            f"Verification plan {plan_name!r} is not declared",
        )
    if not isinstance(raw_plan, dict):
        return _failure(
            "verification_configuration_error",
            f"[verify.{plan_name}] must be a table",
        )
    unknown = sorted(set(raw_plan) - {"checks"})
    if unknown:
        return _failure(
            "verification_configuration_error",
            f"[verify.{plan_name}] contains unknown keys: {unknown}",
        )
    raw_checks = raw_plan.get("checks")
    if not isinstance(raw_checks, list) or not raw_checks:
        return _failure(
            "verification_configuration_error",
            f"[verify.{plan_name}] must contain at least one check",
        )
    if len(raw_checks) > _MAX_CHECKS:
        return _failure(
            "verification_configuration_error",
            f"Verification plan exceeds {_MAX_CHECKS} checks",
        )

    try:
        checks = tuple(_check(item, index) for index, item in enumerate(raw_checks))
    except ValueError as exc:
        return _failure("verification_configuration_error", str(exc))
    names = [check.name for check in checks]
    if len(names) != len(set(names)):
        return _failure(
            "verification_configuration_error",
            "Verification check names must be unique within a plan",
        )
    return VerificationPlanLoadResult(plan=VerificationPlan(name=plan_name, checks=checks))
