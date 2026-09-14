"""Safe remote command preparation for T6 fixtures."""

from cospaces.fixture_config import FixtureDefinition

FIXTURE_SETUP_MARKER = "__cospaces_fixture_setup__"
FIXTURE_SETUP_EXIT_CODES = frozenset({96, 97, 98, 99})
OUTPUT_CHECK_MARKER = "__cospaces_fixture_output__"
OUTPUT_CHECK_EXIT_CODES = frozenset({94, 95, 99})

_ROOT_FAILURE = f'printf "%s\\n" "{FIXTURE_SETUP_MARKER}:root" >&2; exit 97'
_CWD_FAILURE = f'printf "%s\\n" "{FIXTURE_SETUP_MARKER}:cwd" >&2; exit 98'
_INPUT_FAILURE = f'printf "%s\\n" "{FIXTURE_SETUP_MARKER}:input" >&2; exit 96'
_ESCAPE_FAILURE = f'printf "%s\\n" "{FIXTURE_SETUP_MARKER}:escape" >&2; exit 99'
_OUTPUT_ROOT_FAILURE = f'printf "%s\\n" "{OUTPUT_CHECK_MARKER}:root" >&2; exit 94'
_OUTPUT_MISSING = f'printf "%s\\n" "{OUTPUT_CHECK_MARKER}:missing" >&2; exit 95'
_OUTPUT_ESCAPE = f'printf "%s\\n" "{OUTPUT_CHECK_MARKER}:escape" >&2; exit 99'

_FIXTURE_SCRIPT = (
    'repo_name="${GITHUB_REPOSITORY##*/}"; root="/workspaces/$repo_name"; '
    f'[ -n "$repo_name" ] && [ -d "$root" ] || {{ {_ROOT_FAILURE}; }}; '
    f'root_real=$(cd "$root" 2>/dev/null && pwd -P) || {{ {_ROOT_FAILURE}; }}; '
    "work=$1; shift; "
    f'work_real=$(cd "$root/$work" 2>/dev/null && pwd -P) || {{ {_CWD_FAILURE}; }}; '
    f'case "$work_real" in "$root_real"|"$root_real"/*) ;; *) {_ESCAPE_FAILURE} ;; esac; '
    'cd "$work_real" || exit 98; count=$1; shift; i=0; '
    'while [ "$i" -lt "$count" ]; do '
    f'candidate=$(readlink -f -- "$root/$1" 2>/dev/null) || {{ {_INPUT_FAILURE}; }}; '
    f'case "$candidate" in "$root_real"|"$root_real"/*) ;; *) {_ESCAPE_FAILURE} ;; esac; '
    f'[ -e "$candidate" ] || {{ {_INPUT_FAILURE}; }}; '
    'shift; i=$((i + 1)); done; "$@"'
)

_OUTPUT_SCRIPT = (
    'repo_name="${GITHUB_REPOSITORY##*/}"; root="/workspaces/$repo_name"; '
    f'[ -n "$repo_name" ] && [ -d "$root" ] || {{ {_OUTPUT_ROOT_FAILURE}; }}; '
    f'root_real=$(cd "$root" 2>/dev/null && pwd -P) || {{ {_OUTPUT_ROOT_FAILURE}; }}; '
    "count=$1; shift; i=0; "
    'while [ "$i" -lt "$count" ]; do '
    f'candidate=$(readlink -f -- "$root/$1" 2>/dev/null) || {{ {_OUTPUT_MISSING}; }}; '
    f'case "$candidate" in "$root_real"|"$root_real"/*) ;; *) {_OUTPUT_ESCAPE} ;; esac; '
    f'[ -e "$candidate" ] || {{ {_OUTPUT_MISSING}; }}; '
    "shift; i=$((i + 1)); done"
)

_HEAD_SCRIPT = (
    'repo_name="${GITHUB_REPOSITORY##*/}"; root="/workspaces/$repo_name"; '
    '[ -n "$repo_name" ] && [ -d "$root" ] || exit 97; '
    'root_real=$(cd "$root" 2>/dev/null && pwd -P) || exit 97; '
    'git -C "$root_real" rev-parse HEAD'
)


def _value(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return str(value)


def build_fixture_argv(fixture: FixtureDefinition) -> tuple[str, ...]:
    command = fixture.command
    assignments: list[str] = []
    if fixture.seed is not None:
        assignments.append(f"COSPACES_FIXTURE_SEED={_value(fixture.seed)}")
    for name, value in sorted(fixture.parameters.items()):
        assignments.append(f"COSPACES_FIXTURE_PARAM_{name.upper()}={_value(value)}")
    if assignments:
        command = ("env", *assignments, *command)
    return (
        "sh",
        "-c",
        _FIXTURE_SCRIPT,
        "cospaces-fixture",
        fixture.working_directory,
        str(len(fixture.inputs)),
        *fixture.inputs,
        *command,
    )


def build_output_check_argv(outputs: tuple[str, ...]) -> tuple[str, ...]:
    return (
        "sh",
        "-c",
        _OUTPUT_SCRIPT,
        "cospaces-fixture-output",
        str(len(outputs)),
        *outputs,
    )


def build_head_probe_argv() -> tuple[str, ...]:
    return ("sh", "-c", _HEAD_SCRIPT, "cospaces-fixture-head")
