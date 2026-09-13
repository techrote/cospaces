from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.adapters.process import CommandResult
from cospaces.services.run_transport import CodespaceSshTransport, encode_remote_argv, parse_gh_version


class FakeGitHub(GitHubCliAdapter):
    def __init__(self, responses: list[CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], float | None]] = []

    def capture(
        self,
        arguments: tuple[str, ...],
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        self.calls.append((arguments, timeout_seconds))
        return self.responses.pop(0)


def result(
    stdout: str = "",
    *,
    returncode: int | None = 0,
    stderr: str = "",
    timed_out: bool = False,
) -> CommandResult:
    return CommandResult(
        argv=("gh",),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


def test_remote_argv_is_posix_quoted_without_local_shell_interpolation() -> None:
    encoded = encode_remote_argv(("printf", "%s", "a b", "$(touch nope)", "x'y"))

    assert encoded == "set -- printf %s 'a b' '$(touch nope)' 'x'\"'\"'y'; \"$@\""


def test_version_parser_accepts_current_gh_format() -> None:
    assert parse_gh_version("gh version 2.99.1 (2026-01-01)\n") == (2, 99, 1)


def test_transport_targets_exact_codespace_and_forwards_timeout() -> None:
    github = FakeGitHub(
        [
            result("gh version 2.99.1 (2026-01-01)\n"),
            result("done\n"),
        ]
    )
    transport = CodespaceSshTransport(github)

    outcome = transport.execute("space-one", ("echo", "a b"), timeout_seconds=7.5)

    assert outcome.failure is None
    assert outcome.result is not None
    assert outcome.result.stdout == "done\n"
    assert github.calls == [
        (("--version",), 10.0),
        (
            (
                "codespace",
                "ssh",
                "--codespace",
                "space-one",
                "--",
                "-T",
                "-oBatchMode=yes",
                "set -- echo 'a b'; \"$@\"",
            ),
            7.5,
        ),
    ]


def test_transport_refuses_github_cli_affected_by_codespaces_ssh_advisory() -> None:
    github = FakeGitHub([result("gh version 2.61.0 (2024-01-01)\n")])
    transport = CodespaceSshTransport(github)

    outcome = transport.execute("space-one", ("true",), timeout_seconds=3.0)

    assert outcome.result is None
    assert outcome.failure is not None
    assert outcome.failure.code == "unsafe_github_cli_version"
    assert len(github.calls) == 1


def test_transport_returns_timeout_result_without_retry() -> None:
    github = FakeGitHub(
        [
            result("gh version 2.99.1 (2026-01-01)\n"),
            result("partial", returncode=None, stderr="diag", timed_out=True),
        ]
    )
    transport = CodespaceSshTransport(github)

    outcome = transport.execute("space-one", ("slow-task",), timeout_seconds=1.0)

    assert outcome.failure is None
    assert outcome.result is not None
    assert outcome.result.timed_out is True
    assert len(github.calls) == 2
