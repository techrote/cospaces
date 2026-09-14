"""Dispatch T6 fixture execution."""

import argparse
from pathlib import Path

from cospaces.fixture_output import emit_fixture_result
from cospaces.services.fixture_service import FixtureRequest, FixtureService


def run_fixture(namespace: argparse.Namespace) -> int:
    service = FixtureService()
    result = service.execute(
        FixtureRequest(
            fixture=namespace.fixture,
            repository=namespace.repo,
            ref=namespace.ref,
            codespace=namespace.codespace,
            root=Path(namespace.root),
            task_id=namespace.task_id,
            correlation_id=namespace.correlation_id,
        )
    )
    return emit_fixture_result(namespace, result)
