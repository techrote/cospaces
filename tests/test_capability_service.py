from pathlib import Path

from cospaces.adapters.process import CommandResult
from cospaces.domain.capabilities import CapabilityState
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.capability_service import CapabilityRequest, CapabilityService
from cospaces.services.run_service import RunActionResult
from cospaces.services.workspace_service import WorkspaceActionResult

WORKSPACE = WorkspaceIdentity(
    name="space-one",
    repository="owner/repo",
    ref="main",
    state="available",
    display_name="Space One",
    machine="standardLinux32gb",
)


class FakeWorkspace:
    def describe(self, name: str) -> WorkspaceActionResult:
        assert name == WORKSPACE.name
        return WorkspaceActionResult(workspace=WORKSPACE)

    def resolve(self, repository: str, *, ref=None, name=None) -> WorkspaceActionResult:
        assert repository == WORKSPACE.repository
        assert ref in (None, WORKSPACE.ref)
        assert name in (None, WORKSPACE.name)
        return WorkspaceActionResult(workspace=WORKSPACE)


class FakeGitHub:
    def __init__(self, result: CommandResult | BaseException) -> None:
        self.result = result

    def capture(self, arguments: tuple[str, ...], *, timeout_seconds=None) -> CommandResult:
        assert arguments == ("--version",)
        assert timeout_seconds == 10.0
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class FakeRun:
    def __init__(self, results: list[RunActionResult]) -> None:
        self.results = results
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.results.pop(0)


def command_result(stdout: str, *, returncode: int = 0) -> CommandResult:
    return CommandResult(
        argv=("gh",),
        returncode=returncode,
        stdout=stdout,
        stderr="",
        timed_out=False,
    )


def run_result(
    argv: tuple[str, ...],
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    failure: DomainFailure | None = None,
    run_id: str = "run-1",
) -> RunActionResult:
    record = RunRecord(
        run_id=run_id,
        argv=argv,
        task_id="capabilities",
        correlation_id="probe",
        timeout_seconds=10.0,
        exit_code=exit_code,
        timed_out=failure is not None and failure.code == "remote_timeout",
        remote_completion="success" if failure is None else "failed",
        transport="gh-codespace-ssh",
        stdout=stdout,
        stderr=stderr,
        stderr_mixed=True,
        duration_seconds=0.1,
        started_at="2026-09-14T00:00:00Z",
        finished_at="2026-09-14T00:00:01Z",
    )
    return RunActionResult(record=record, workspace=WORKSPACE, failure=failure)


def test_capabilities_distinguishes_present_absent_and_unknown(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[capabilities.supports]\n"
        "build = true\n"
        "[[capabilities.probes]]\n"
        'name = "python"\n'
        'command = ["python", "--version"]\n'
        'version_regex = "Python ([0-9.]+)"\n'
        "[[capabilities.probes]]\n"
        'name = "missing"\n'
        'command = ["definitely-missing-tool", "--version"]\n'
        "[[capabilities.probes]]\n"
        'name = "odd"\n'
        'command = ["odd", "--version"]\n'
        'version_regex = "odd ([0-9.]+)"\n',
        encoding="utf-8",
    )
    missing = DomainFailure(
        code="remote_task_failed",
        kind=FailureKind.REMOTE,
        message="failed",
    )
    fake_run = FakeRun(
        [
            run_result(("uname", "-s"), stdout="Linux\n", run_id="os"),
            run_result(("uname", "-m"), stdout="x86_64\n", run_id="arch"),
            run_result(("python", "--version"), stdout="Python 3.11.9\n", run_id="python"),
            run_result(
                ("definitely-missing-tool", "--version"),
                stderr="not found\n",
                exit_code=127,
                failure=missing,
                run_id="missing",
            ),
            run_result(("odd", "--version"), stdout="unexpected\n", run_id="odd"),
        ]
    )
    service = CapabilityService(
        workspace=FakeWorkspace(),  # type: ignore[arg-type]
        run=fake_run,  # type: ignore[arg-type]
        github=FakeGitHub(command_result("gh version 2.80.0\n")),  # type: ignore[arg-type]
    )

    result = service.inspect(CapabilityRequest(repository="owner/repo", ref="main", root=tmp_path))

    assert result.ok
    assert result.report is not None
    assert result.report.declared_support == {"build": True}
    assert result.report.github_cli.state == CapabilityState.PRESENT
    assert result.report.github_cli.version == "2.80.0"
    observations = {item.name: item for item in result.report.observations}
    assert observations["remote_os"].value == "Linux"
    assert observations["remote_architecture"].value == "x86_64"
    assert observations["python"].state == CapabilityState.PRESENT
    assert observations["python"].version == "3.11.9"
    assert observations["missing"].state == CapabilityState.ABSENT
    assert observations["missing"].reason == "executable_unavailable"
    assert observations["odd"].state == CapabilityState.UNKNOWN
    assert observations["odd"].version is None
    assert observations["odd"].reason == "version_parse_failed"
    assert all(request.codespace == WORKSPACE.name for request in fake_run.requests)


def test_probe_timeout_is_unavailable_not_absent(tmp_path: Path) -> None:
    timeout = DomainFailure(
        code="remote_timeout",
        kind=FailureKind.REMOTE,
        message="timeout",
    )
    fake_run = FakeRun(
        [
            run_result(("uname", "-s"), failure=timeout, exit_code=0, run_id="os"),
            run_result(("uname", "-m"), stdout="x86_64\n", run_id="arch"),
        ]
    )
    service = CapabilityService(
        workspace=FakeWorkspace(),  # type: ignore[arg-type]
        run=fake_run,  # type: ignore[arg-type]
        github=FakeGitHub(command_result("gh version 2.80.0\n")),  # type: ignore[arg-type]
    )

    result = service.inspect(CapabilityRequest(repository="owner/repo", root=tmp_path))

    assert result.ok
    assert result.report is not None
    observations = {item.name: item for item in result.report.observations}
    assert observations["remote_os"].state == CapabilityState.UNAVAILABLE
    assert observations["remote_os"].reason == "remote_timeout"


def test_github_cli_version_parse_failure_is_unknown(tmp_path: Path) -> None:
    fake_run = FakeRun(
        [
            run_result(("uname", "-s"), stdout="Linux\n", run_id="os"),
            run_result(("uname", "-m"), stdout="x86_64\n", run_id="arch"),
        ]
    )
    service = CapabilityService(
        workspace=FakeWorkspace(),  # type: ignore[arg-type]
        run=fake_run,  # type: ignore[arg-type]
        github=FakeGitHub(command_result("mystery gh build\n")),  # type: ignore[arg-type]
    )

    result = service.inspect(CapabilityRequest(repository="owner/repo", root=tmp_path))

    assert result.ok
    assert result.report is not None
    assert result.report.github_cli.state == CapabilityState.UNKNOWN
    assert result.report.github_cli.version is None
    assert result.report.github_cli.reason == "version_parse_failed"


def test_workspace_selection_failure_aborts_before_remote_probes(tmp_path: Path) -> None:
    failure = DomainFailure(
        code="workspace_not_found",
        kind=FailureKind.SELECTION,
        message="not found",
    )

    class MissingWorkspace(FakeWorkspace):
        def resolve(self, repository: str, *, ref=None, name=None) -> WorkspaceActionResult:
            return WorkspaceActionResult(failure=failure)

    fake_run = FakeRun([])
    service = CapabilityService(
        workspace=MissingWorkspace(),  # type: ignore[arg-type]
        run=fake_run,  # type: ignore[arg-type]
        github=FakeGitHub(command_result("gh version 2.80.0\n")),  # type: ignore[arg-type]
    )

    result = service.inspect(CapabilityRequest(repository="owner/repo", root=tmp_path))

    assert not result.ok
    assert result.failure == failure
    assert fake_run.requests == []
