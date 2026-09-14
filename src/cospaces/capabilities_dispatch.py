"""Dispatch T5 capability inspection."""

import argparse
from pathlib import Path

from cospaces.capabilities_output import emit_capability_result
from cospaces.services.capability_service import CapabilityRequest, CapabilityService


def run_capabilities(namespace: argparse.Namespace) -> int:
    service = CapabilityService()
    result = service.inspect(
        CapabilityRequest(
            repository=namespace.repo,
            ref=namespace.ref,
            codespace=namespace.codespace,
            root=Path(namespace.root),
        )
    )
    return emit_capability_result(namespace, result)
