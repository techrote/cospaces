"""Verify command dispatch."""

import argparse
from pathlib import Path

from cospaces.services.verification_service import VerificationRequest, VerificationService
from cospaces.verify_output import emit_verification_result


def run_verify(
    namespace: argparse.Namespace,
    service: VerificationService | None = None,
) -> int:
    root = service.root if service is not None else Path(str(namespace.root)).resolve()
    active = service or VerificationService(root)
    result = active.verify(
        VerificationRequest(
            plan=str(namespace.plan),
            codespace=namespace.codespace,
            repository=namespace.repo,
            ref=namespace.ref,
            task_id=namespace.task_id,
            correlation_id=namespace.correlation_id,
        )
    )
    return emit_verification_result(namespace, result)
