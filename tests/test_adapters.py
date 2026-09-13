import subprocess
from collections.abc import Mapping

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult, ProcessAdapter


class FakeProcess(ProcessAdapter):
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], Mapping[str, str] | None, float | None]] = []

    def capture(
        self,
        argv: tuple[str, ...],
        *,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        self.calls.append((argv, environment, timeout_seconds))
        return CommandResult(argv=argv, returncode=0, stdout="ok", stderr="")


def test_process_adapter_uses_argv_disables_shell_and_merges_environment(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["shell"] = kwargs["shell"]
        observed["marker"] = kwargs["env"]["COSPACES_TEST_MARKER"]
        observed["timeout"] = kwargs["timeout"]
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("cospaces.adapters.process.subprocess.run", fake_run)

    result = ProcessAdapter().capture(
        ("example", "--flag"),
        environment={"COSPACES_TEST_MARKER": "yes"},
        timeout_seconds=12.5,
    )

    assert observed == {
        "argv": ("example", "--flag"),
        "shell": False,
        "marker": "yes",
        "timeout": 12.5,
    }
    assert result.returncode == 0
    assert result.stdout == "ok"


def test_process_adapter_returns_partial_output_on_timeout(monkeypatch) -> None:
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output="partial", stderr="diag")

    monkeypatch.setattr("cospaces.adapters.process.subprocess.run", fake_run)

    result = ProcessAdapter().capture(("example",), timeout_seconds=1.0)

    assert result.returncode is None
    assert result.timed_out is True
    assert result.stdout == "partial"
    assert result.stderr == "diag"


def test_github_cli_adapter_disables_prompts_and_forwards_timeout() -> None:
    fake = FakeProcess()
    adapter = GitHubCliAdapter(process=fake)

    result = adapter.capture(("codespace", "list"), timeout_seconds=3.0)

    assert fake.calls == [(("gh", "codespace", "list"), {"GH_PROMPT_DISABLED": "1"}, 3.0)]
    assert result.stdout == "ok"
