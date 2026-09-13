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


def run_result(run_id: str, *, failed: bool = False) -> RunActionResult:
    failure = None
    exit_code = 0
    completion = "success"
    if failed:
        failure = DomainFailure(
            code="remote_task_failed",
            kind=FailureKind.REMOTE,
            message="declared check failed",
        )
        exit_code = 9
        completion = "failed"
    return RunActionResult(
        workspace=target(),
        record=RunRecord(
            run_id=run_id,
            argv=("example",),
            task_id="issue-18",
            correlation_id="verification",
            timeout_seconds=60.0,
            exit_code=exit_code,
            timed_out=False,
            remote_completion=completion,
            transport="gh-codespace-ssh",
            stdout="",
            stderr="",
            stderr_mixed=True,
            duration_seconds=0.01,
            started_at="2026-09-13T20:00:00Z",
            finished_at="2026-09-13T20:00:00.010000Z",
        ),
        failure=failure,
    )


def write_plan(root: Path) -> None:
    (root / ".cospaces.toml").write_text(
        "[verify.default]\n"
        '[[verify.default.checks]]\nname = "first"\ncommand = ["example-one"]\n'
        '[[verify.default.checks]]\nname = "second"\ncommand = ["example-two"]\n',
        encoding="utf-8",
    )
