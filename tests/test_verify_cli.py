import json
from pathlib import Path

from cospaces.cli import build_parser, main
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.verification import VerificationCheckRecord, VerificationRecord
from cospaces.services.verification_service import VerificationActionResult
from cospaces.verify_dispatch import run_verify


class FakeVerificationService:
    def __init__(self, root: Path, result: VerificationActionResult) -> None:
        self.root = root
        self.result = result
        self.requests = []

    def verify(self, request):
        self.requests.append(request)
        return self.result


def record(*, passed: bool = True) -> VerificationRecord:
    return VerificationRecord(
        verification_id="11111111-1111-4111-8111-111111111111",
        plan="default",
        task_id="issue-5",
        correlation_id="chat-1",
        repository="owner/repo",
        ref="main",
        head="abc123",
        workspace={"name": "space-one"},
        started_at="2026-09-13T20:00:00Z",
        finished_at="2026-09-13T20:00:01Z",
        complete=True,
        passed=passed,
        checks=(
            VerificationCheckRecord(
                name="tests",
                required=True,
                passed=passed,
                timed_out=False,
                run_id="run-1",
                exit_code=0 if passed else 1,
                remote_completion="success" if passed else "failed",
                duration_ms=1000,
                failure_code=None if passed else "remote_task_failed",
                command=("python", "-m", "pytest"),
                working_directory=None,
                environment_keys=(),
            ),
        ),
    )


def test_verify_json_is_one_document_with_provenance(tmp_path, capsys) -> None:
    namespace = build_parser().parse_args(
        [
            "verify",
            "default",
            "--codespace",
            "space-one",
            "--task-id",
            "issue-5",
            "--correlation-id",
            "chat-1",
            "--json",
        ]
    )
    service = FakeVerificationService(tmp_path, VerificationActionResult(record=record()))

    status = run_verify(namespace, service)  # type: ignore[arg-type]

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 0
    assert captured.err == ""
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "verify"
    assert payload["ok"] is True
    assert payload["workspace"]["name"] == "space-one"
    assert payload["result"]["schema"] == "cospaces.verify/v1"
    assert payload["result"]["verification_id"] == "11111111-1111-4111-8111-111111111111"
    assert payload["result"]["checks"][0]["run_id"] == "run-1"
    assert service.requests[0].task_id == "issue-5"
    assert service.requests[0].correlation_id == "chat-1"


def test_required_failure_returns_verification_exit_category(tmp_path, capsys) -> None:
    failure = DomainFailure(
        code="verification_failed",
        kind=FailureKind.VERIFICATION,
        message="required check failed",
    )
    namespace = build_parser().parse_args(["verify", "--codespace", "space-one", "--json"])
    service = FakeVerificationService(
        tmp_path,
        VerificationActionResult(record=record(passed=False), failure=failure),
    )

    status = run_verify(namespace, service)  # type: ignore[arg-type]

    payload = json.loads(capsys.readouterr().out)
    assert status == 7
    assert payload["ok"] is False
    assert payload["result"]["passed"] is False
    assert payload["error"]["code"] == "verification_failed"


def test_missing_repository_config_fails_before_remote_execution(tmp_path, capsys) -> None:
    status = main(
        [
            "verify",
            "--root",
            str(tmp_path),
            "--repo",
            "owner/repo",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 2
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "verification_config_missing"
