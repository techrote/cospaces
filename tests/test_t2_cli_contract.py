import json

from cospaces.cli import build_parser
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.run_dispatch import parse_timeout, run_remote
from cospaces.services.run_service import RunActionResult


class FakeRunService:
    def __init__(self) -> None:
        self.request = None

    def execute(self, request):
        self.request = request
        return RunActionResult(
            workspace=WorkspaceIdentity(
                name="space-one",
                repository="owner/repo",
                ref="main",
                state="available",
                display_name="space-one",
                machine="standard",
            ),
            record=RunRecord(
                run_id="11111111-1111-4111-8111-111111111111",
                argv=request.argv,
                task_id=request.task_id,
                correlation_id=request.correlation_id,
                timeout_seconds=request.timeout_seconds,
                exit_code=0,
                timed_out=False,
                remote_completion="success",
                transport="gh-codespace-ssh",
                stdout="hello\n",
                stderr="",
                stderr_mixed=True,
                duration_seconds=0.25,
                started_at="2026-09-13T19:00:00Z",
                finished_at="2026-09-13T19:00:00.250000Z",
            ),
        )


def test_timeout_parser_supports_seconds_minutes_and_hours() -> None:
    assert parse_timeout("5") == 5.0
    assert parse_timeout("2.5s") == 2.5
    assert parse_timeout("10m") == 600.0
    assert parse_timeout("1h") == 3600.0
    assert parse_timeout("nonsense") is None


def test_parser_preserves_explicit_task_boundary_and_arguments() -> None:
    namespace = build_parser().parse_args(
        [
            "run",
            "--codespace",
            "space-one",
            "--timeout",
            "10m",
            "--task-id",
            "issue-3",
            "--correlation-id",
            "chat-1",
            "--json",
            "--",
            "printf",
            "%s",
            "a b",
            "--literal",
        ]
    )

    assert namespace.remote_argv == ["--", "printf", "%s", "a b", "--literal"]
