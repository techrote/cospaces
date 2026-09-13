import subprocess

from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult, ProcessAdapter


class FakeProcess(ProcessAdapter):
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def capture(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        return CommandResult(argv=argv, returncode=0, stdout="ok", stderr="")


def test_process_adapter_uses_argv_and_disables_shell(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["shell"] = kwargs["shell"]
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("cospaces.adapters.process.subprocess.run", fake_run)

    result = ProcessAdapter().capture(("example", "--flag"))

    assert observed == {"argv": ("example", "--flag"), "shell": False}
    assert result.returncode == 0
    assert result.stdout == "ok"


def test_github_cli_adapter_can_be_stubbed_without_real_gh() -> None:
    fake = FakeProcess()
    adapter = GitHubCliAdapter(process=fake)

    result = adapter.capture(("codespace", "list"))

    assert fake.calls == [("gh", "codespace", "list")]
    assert result.stdout == "ok"
