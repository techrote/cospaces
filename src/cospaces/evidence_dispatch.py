"""Dispatch T7 evidence operations."""

import argparse
from pathlib import Path

from cospaces.evidence_output import emit_evidence_create, emit_evidence_validation
from cospaces.services.evidence_service import (
    EvidenceCreateRequest,
    EvidenceService,
    EvidenceValidateRequest,
)


def run_evidence(namespace: argparse.Namespace) -> int:
    service = EvidenceService()
    if namespace.evidence_action == "create":
        result = service.create(
            EvidenceCreateRequest(
                plan=namespace.plan,
                root=Path(namespace.root),
                output_directory=namespace.output_directory,
            )
        )
        return emit_evidence_create(namespace, result)
    result = service.validate(
        EvidenceValidateRequest(
            bundle=Path(namespace.bundle),
            root=Path(namespace.root),
        )
    )
    return emit_evidence_validation(namespace, result)
