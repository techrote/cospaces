import subprocess
from collections.abc import Mapping

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult, ProcessAdapter


class FakeProcess(ProcessAdapter):
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], Mapping[str, str] | None]] = []

    def capture(
        self,
        argv: tuple[str, ...],
        *,
        environment: Mapping[str, str] | None = None,
    ) -> CommandResult:
        self.calls.append((argv, environment))
        return CommandResult(argv=argv, returncode=0, stdout="ok", stderr="")


def test_process_adapter_uses_argv_disables_shell_and_merges_environment(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["shell"] = kwargs["shell"]
        observed["marker"] = kwargs["env"]["COSPACES_TEST_MARKER"]
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("cospaces.adapters.process.subprocess.run", fake_run)

    result = ProcessAdapter().capture(
        ("example", "--flag"),
        environment={"COSPACES_TEST_MARKER": "yes"},
    )

    assert observed == {
        "argv": ("example", "--flag"),
        "shell": False,
        "marker": "yes",
    }
    assert result.returncode == 0
    assert result.stdout == "ok"


def test_github_cli_adapter_disables_prompts_and_can_be_stubbed() -> None:
    fake = FakeProcess()
    adapter = GitHubCliAdapter(process=fake)

    result = adapter.capture(("codespace", "list"))

    assert fake.calls == [
        (("gh", "codespace", "list"), {"GH_PROMPT_DISABLED": "1"})
    ]
    assert result.stdout == "ok"
