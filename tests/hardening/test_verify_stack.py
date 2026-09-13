import json
from pathlib import Path

from cospaces.cli import build_parser
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.run_service import RunActionResult
from cospaces.services.verification_service import VerificationService
from cospaces.verify_dispatch import run_verify


class FakeRunService:
    def __init__(self, results: list[RunActionResult]) -> None:
        self.results = results
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.results.pop(0)


def target() -> WorkspaceIdentity:
    return WorkspaceIdentity(
        name="space-one",
        repository="owner/repo",
        ref="main",
        state="available",
        display_name="space-one",
        machine="standard",
    )
