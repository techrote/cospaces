"""Output rendering for T5 capabilities."""

import argparse
import sys

from cospaces.domain.results import ResultEnvelope, utc_now
from cospaces.services.capability_service import CapabilityActionResult


def emit_capability_result(namespace: argparse.Namespace, result: CapabilityActionResult) -> int:
    now = utc_now()
    report = result.report
    envelope = ResultEnvelope(
        operation="capabilities",
        ok=result.ok,
        started_at=now,
        finished_at=now,
        workspace=report.workspace.to_dict() if report is not None else None,
        result=report.to_dict() if report is not None else None,
        error=result.failure,
    )
    if namespace.json_output:
        print(envelope.to_json())
    elif report is not None:
        gh = report.github_cli
        print(f"{gh.state.value}\tcontroller\tgithub_cli\t{gh.version or '-'}")
        for observation in report.observations:
            detail = observation.version or observation.value or observation.reason or "-"
            print(f"{observation.state.value}\tremote\t{observation.name}\t{detail}")
        for name, supported in sorted(report.declared_support.items()):
            print(f"declared\trepository\t{name}\t{str(supported).lower()}")
    elif result.failure is not None:
        print(result.failure.message, file=sys.stderr)
    if result.failure is not None:
        return int(result.failure.exit_status)
    return 0
