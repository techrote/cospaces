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


def run_stack(root: Path, runner: FakeRunService, capsys) -> tuple[int, dict[str, object]]:
    namespace = build_parser().parse_args(
        ["verify", "default", "--codespace", "space-one", "--root", str(root), "--json"]
    )
    service = VerificationService(root, run_service=runner)  # type: ignore[arg-type]
    status = run_verify(namespace, service)
    captured = capsys.readouterr()
    assert captured.err == ""
    return status, json.loads(captured.out)


def test_verify_pass_uses_real_parser_config_service_and_output(tmp_path: Path, capsys) -> None:
    write_plan(tmp_path)
    runner = FakeRunService([run_result("run-a"), run_result("run-b")])

    status, payload = run_stack(tmp_path, runner, capsys)

    assert status == 0
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "verify"
    assert payload["ok"] is True
    result = payload["result"]
    assert isinstance(result, dict)
    assert result["schema"] == "cospaces.verify/v1"
    assert result["passed"] is True
    assert [item["run_id"] for item in result["checks"]] == ["run-a", "run-b"]
    assert len(runner.requests) == 2


def test_verify_required_failure_is_exit_seven_and_keeps_later_check(tmp_path: Path, capsys) -> None:
    write_plan(tmp_path)
    runner = FakeRunService([run_result("run-a", failed=True), run_result("run-b")])

    status, payload = run_stack(tmp_path, runner, capsys)

    assert status == 7
    assert payload["ok"] is False
    assert payload["error"]["code"] == "verification_failed"
    result = payload["result"]
    assert isinstance(result, dict)
    assert result["complete"] is True
    assert result["passed"] is False
    assert len(result["checks"]) == 2
    assert len(runner.requests) == 2
