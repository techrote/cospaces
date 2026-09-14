from cospaces.fixture_command import (
    FIXTURE_SETUP_MARKER,
    OUTPUT_CHECK_MARKER,
    build_fixture_argv,
    build_head_probe_argv,
    build_output_check_argv,
)
from cospaces.fixture_config import FixtureDefinition


def fixture() -> FixtureDefinition:
    return FixtureDefinition(
        name="bench",
        command=("python", "bench.py"),
        timeout_seconds=30.0,
        working_directory="bench",
        tags=("perf",),
        seed=42,
        parameters={"size": 1000, "mode": "fast"},
        inputs=("fixtures/input.json",),
        outputs=("out/result.bin",),
        metrics_format="json-last-line",
        assertions=(),
    )


def test_fixture_command_keeps_dynamic_values_as_positional_argv() -> None:
    argv = build_fixture_argv(fixture())

    assert argv[:2] == ("sh", "-c")
    script = argv[2]
    assert FIXTURE_SETUP_MARKER in script
    assert "pwd -P" in script
    assert "readlink -f" in script
    assert "bench.py" not in script
    assert "fixtures/input.json" not in script
    assert "COSPACES_FIXTURE_SEED=42" in argv
    assert "COSPACES_FIXTURE_PARAM_MODE=fast" in argv
    assert "COSPACES_FIXTURE_PARAM_SIZE=1000" in argv
    assert argv[-2:] == ("python", "bench.py")


def test_output_check_uses_containment_wrapper() -> None:
    argv = build_output_check_argv(("out/result.bin",))

    assert argv[:2] == ("sh", "-c")
    assert OUTPUT_CHECK_MARKER in argv[2]
    assert "readlink -f" in argv[2]
    assert argv[-1] == "out/result.bin"


def test_head_probe_observes_remote_checkout() -> None:
    argv = build_head_probe_argv()

    assert argv[:2] == ("sh", "-c")
    assert 'git -C "$root_real" rev-parse HEAD' in argv[2]
