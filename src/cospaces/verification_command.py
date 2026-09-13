"""Safe argv preparation for verification checks."""

from cospaces.domain.verification import VerificationCheck

VERIFY_SETUP_MARKER = "__cospaces_verify_setup__"
VERIFY_SETUP_EXIT_CODES = frozenset({97, 98, 99})

_ROOT_FAILURE = f'printf "%s\\n" "{VERIFY_SETUP_MARKER}:root" >&2; exit 97'
_CWD_FAILURE = f'printf "%s\\n" "{VERIFY_SETUP_MARKER}:cwd" >&2; exit 98'
_ESCAPE_FAILURE = f'printf "%s\\n" "{VERIFY_SETUP_MARKER}:escape" >&2; exit 99'

_VERIFY_CWD_SCRIPT = (
    'repo_name="${GITHUB_REPOSITORY##*/}"; '
    'root="/workspaces/$repo_name"; '
    f'[ -n "$repo_name" ] && [ -d "$root" ] || {{ {_ROOT_FAILURE}; }}; '
    f'root_real=$(cd "$root" 2>/dev/null && pwd -P) || {{ {_ROOT_FAILURE}; }}; '
    f'target_real=$(cd "$root/$1" 2>/dev/null && pwd -P) || {{ {_CWD_FAILURE}; }}; '
    f'case "$target_real" in "$root_real"|"$root_real"/*) ;; *) '
    f"{_ESCAPE_FAILURE} ;; esac; "
    f'cd "$target_real" || {{ {_CWD_FAILURE}; }}; '
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
