"""Safe argv preparation for verification checks."""

from cospaces.domain.verification import VerificationCheck

VERIFY_SETUP_MARKER = "__cospaces_verify_setup__"
VERIFY_SETUP_EXIT_CODES = frozenset({97, 98, 99})

_VERIFY_CWD_SCRIPT = (
    'repo_name="${GITHUB_REPOSITORY##*/}"; '
    'root="/workspaces/$repo_name"; '
    f'[ -n "$repo_name" ] && [ -d "$root" ] || {{ printf "%s\\n" "{VERIFY_SETUP_MARKER}:root" >&2; exit 97; }}; '
    f'root_real=$(cd "$root" 2>/dev/null && pwd -P) || {{ printf "%s\\n" "{VERIFY_SETUP_MARKER}:root" >&2; exit 97; }}; '
    f'target_real=$(cd "$root/$1" 2>/dev/null && pwd -P) || {{ printf "%s\\n" "{VERIFY_SETUP_MARKER}:cwd" >&2; exit 98; }}; '
    f'case "$target_real" in "$root_real"|"$root_real"/*) ;; *) printf "%s\\n" "{VERIFY_SETUP_MARKER}:escape" >&2; exit 99 ;; esac; '
    f'cd "$target_real" || {{ printf "%s\\n" "{VERIFY_SETUP_MARKER}:cwd" >&2; exit 98; }}; '
    'shift; exec "$@"'
)


def build_check_argv(check: VerificationCheck) -> tuple[str, ...]:
    command = check.command
    if check.environment:
        assignments = tuple(f"{key}={value}" for key, value in check.environment)
        command = ("env", *assignments, *command)
    working_directory = check.working_directory or "."
    return (
        "sh",
        "-c",
        _VERIFY_CWD_SCRIPT,
        "cospaces-verify",
        working_directory,
        *command,
    )
