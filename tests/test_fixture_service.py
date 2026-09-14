from pathlib import Path

from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.fixture_service import FixtureRequest, FixtureService
from cospaces.services.run_service import RunActionResult

WORKSPACE = WorkspaceIdentity(
    name="space-one",
    repository="owner/repo",
    ref="main",
    state="available",
    display_name="Space One",
    machine="standard",
)
HEAD = "a" * 40


class FakeRun:
    def __init__(self, results: list[RunActionResult]) -> None:
        self.results = results
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.results.pop(0)


def remote_failure() -> DomainFailure:
    return DomainFailure(
        code="remote_task_failed",
        kind=FailureKind.REMOTE,
        message="remote task failed",
    )


def run_result(
    *,
    run_id: str,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    failure: DomainFailure | None = None,
    workspace: WorkspaceIdentity | None = WORKSPACE,
) -> RunActionResult:
    return RunActionResult(
        record=RunRecord(
            run_id=run_id,
            argv=("remote",),
            task_id="fixture:bench",
            correlation_id="fixture-run",
            timeout_seconds=30.0,
            exit_code=exit_code,
            timed_out=False,
            remote_completion="success" if failure is None else "failed",
            transport="gh-codespace-ssh",
            stdout=stdout,
            stderr=stderr,
            stderr_mixed=True,
            duration_seconds=0.1,
            started_at="2026-09-14T00:00:00Z",
            finished_at="2026-09-14T00:00:01Z",
        ),
        workspace=workspace,
        failure=failure,
    )


def write_fixture(tmp_path: Path, *, assertion_value: int = 10) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[fixture.bench]\n"
        'command = ["python", "bench.py"]\n'
        'working_directory = "bench"\n'
        "seed = 42\n"
        'inputs = ["fixtures/input.json"]\n'
        'outputs = ["out/result.bin"]\n'
        'metrics_format = "json-last-line"\n'
        "[fixture.bench.parameters]\n"
        "size = 1000\n"
        "[[fixture.bench.assertions]]\n"
        'metric = "throughput"\n'
        'operator = ">="\n'
        f"value = {assertion_value}\n",
        encoding="utf-8",
    )


def test_fixture_passes_with_observed_head_metrics_assertions_and_outputs(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    fake = FakeRun(
        [
            run_result(run_id="head", stdout=HEAD + "\n"),
            run_result(run_id="task", stdout='progress\n{"throughput":12.5,"items":1000}\n'),
            run_result(run_id="outputs"),
        ]
    )
    service = FixtureService(run=fake)  # type: ignore[arg-type]

    result = service.execute(
        FixtureRequest(fixture="bench", repository="owner/repo", ref="main", root=tmp_path)
    )

    assert result.ok
    assert result.record is not None
    record = result.record
    assert record.schema == "cospaces.fixture/v1"
    assert record.head == HEAD
    assert record.task_run_id == "task"
    assert record.support_run_ids == ("head", "outputs")
    assert len(record.definition_digest) == 64
    assert record.metrics == {"throughput": 12.5, "items": 1000}
    assert record.assertions[0].passed is True
    assert record.complete is True
    assert record.passed is True
    assert [request.codespace for request in fake.requests] == [None, "space-one", "space-one"]
    assert fake.requests[1].repository == "owner/repo"
    assert fake.requests[1].ref == "main"


def test_fixture_input_setup_failure_is_distinct(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    fake = FakeRun(
        [
            run_result(run_id="head", stdout=HEAD),
            run_result(run_id="task", exit_code=96, failure=remote_failure()),
        ]
    )

    result = FixtureService(run=fake).execute(  # type: ignore[arg-type]
        FixtureRequest(fixture="bench", repository="owner/repo", root=tmp_path)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_input_missing"
    assert result.record is not None
    assert result.record.head == HEAD
    assert result.record.complete is False


def test_fixture_remote_task_failure_is_distinct(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    fake = FakeRun(
        [
            run_result(run_id="head", stdout=HEAD),
            run_result(run_id="task", exit_code=2, failure=remote_failure()),
        ]
    )

    result = FixtureService(run=fake).execute(  # type: ignore[arg-type]
        FixtureRequest(fixture="bench", repository="owner/repo", root=tmp_path)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_task_failed"
    assert result.failure.kind == FailureKind.REMOTE


def test_fixture_metrics_parse_failure_is_complete_but_failed(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    fake = FakeRun(
        [
            run_result(run_id="head", stdout=HEAD),
            run_result(run_id="task", stdout="not-json\n"),
            run_result(run_id="outputs"),
        ]
    )

    result = FixtureService(run=fake).execute(  # type: ignore[arg-type]
        FixtureRequest(fixture="bench", repository="owner/repo", root=tmp_path)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_metrics_parse_failed"
    assert result.record is not None
    assert result.record.complete is True
    assert result.record.passed is False


def test_fixture_assertion_failure_is_structured(tmp_path: Path) -> None:
    write_fixture(tmp_path, assertion_value=20)
    fake = FakeRun(
        [
            run_result(run_id="head", stdout=HEAD),
            run_result(run_id="task", stdout='{"throughput":12.5}\n'),
            run_result(run_id="outputs"),
        ]
    )

    result = FixtureService(run=fake).execute(  # type: ignore[arg-type]
        FixtureRequest(fixture="bench", repository="owner/repo", root=tmp_path)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_assertion_failed"
    assert result.record is not None
    assert result.record.complete is True
    assert result.record.assertions[0].passed is False
    assert result.record.assertions[0].actual == 12.5


def test_fixture_output_missing_is_distinct(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    fake = FakeRun(
        [
            run_result(run_id="head", stdout=HEAD),
            run_result(run_id="task", stdout='{"throughput":12.5}\n'),
            run_result(run_id="outputs", exit_code=95, failure=remote_failure()),
        ]
    )

    result = FixtureService(run=fake).execute(  # type: ignore[arg-type]
        FixtureRequest(fixture="bench", repository="owner/repo", root=tmp_path)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_output_missing"
    assert result.record is not None
    assert result.record.complete is False


def test_fixture_provenance_failure_prevents_task_execution(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    fake = FakeRun([run_result(run_id="head", stdout="not-a-sha\n")])

    result = FixtureService(run=fake).execute(  # type: ignore[arg-type]
        FixtureRequest(fixture="bench", repository="owner/repo", root=tmp_path)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_provenance_failed"
    assert result.record is None
    assert len(fake.requests) == 1
