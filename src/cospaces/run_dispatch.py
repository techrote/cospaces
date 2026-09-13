"""Run command parsing and dispatch."""

import argparse
import re

from cospaces.domain.run import RunRequest
from cospaces.run_output import emit_run_result
from cospaces.services.run_service import RunService

_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)([smh]?)$")
_FACTORS = {"": 1.0, "s": 1.0, "m": 60.0, "h": 3600.0}


def parse_timeout(value: str) -> float | None:
    match = _DURATION_RE.fullmatch(value.strip().casefold())
    if match is None:
        return None
    return float(match.group(1)) * _FACTORS[match.group(2)]


def run_remote(
    namespace: argparse.Namespace,
    service: RunService | None = None,
) -> int:
    raw = tuple(str(item) for item in namespace.remote_argv)
    boundary_present = bool(raw) and raw[0] == "--"
    argv = raw[1:] if boundary_present else ()
    timeout = parse_timeout(str(namespace.timeout))
    request = RunRequest(
        argv=argv,
        codespace=namespace.codespace,
        repository=namespace.repo,
        ref=namespace.ref,
        timeout_seconds=timeout if timeout is not None else -1.0,
        task_id=namespace.task_id,
        correlation_id=namespace.correlation_id,
    )
    active = service or RunService()
    result = active.execute(request)
    return emit_run_result(namespace, result)
