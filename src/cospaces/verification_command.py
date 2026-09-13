"""Safe argv preparation for verification checks."""

from cospaces.domain.verification import VerificationCheck

_VERIFY_CWD_SCRIPT = (
    'repo_name="${GITHUB_REPOSITORY##*/}"; '
    'root="/workspaces/$repo_name"; '
    '[ -n "$repo_name" ] && [ -d "$root" ] || exit 97; '
    'cd -- "$root/$1" || exit 98; '
    'shift; exec "$@"'
)


def build_check_argv(check: VerificationCheck) -> tuple[str, ...]:
    command = check.command
    if check.environment:
        assignments = tuple(f"{key}={value}" for key, value in check.environment)
        command = ("env", *assignments, *command)
    if check.working_directory is None:
        return command
    return (
        "sh",
        "-c",
        _VERIFY_CWD_SCRIPT,
        "cospaces-verify",
        check.working_directory,
        *command,
    )
