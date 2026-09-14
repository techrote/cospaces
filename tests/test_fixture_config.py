from pathlib import Path

from cospaces.fixture_config import load_fixture


def write_fixture(tmp_path: Path, body: str) -> None:
    (tmp_path / ".cospaces.toml").write_text(body, encoding="utf-8")


def test_fixture_config_parses_reproducibility_fields(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "[fixture.bench]\n"
        'command = ["python", "bench.py"]\n'
        "timeout_seconds = 30\n"
        'working_directory = "bench"\n'
        'tags = ["perf", "smoke"]\n'
        "seed = 42\n"
        'inputs = ["fixtures/input.json"]\n'
        'outputs = ["out/result.bin"]\n'
        'metrics_format = "json-last-line"\n'
        "[fixture.bench.parameters]\n"
        "size = 1000\n"
        'mode = "fast"\n'
        "[[fixture.bench.assertions]]\n"
        'metric = "throughput"\n'
        'operator = ">="\n'
        "value = 10\n",
    )

    result = load_fixture(tmp_path, "bench")

    assert result.ok
    assert result.fixture is not None
    fixture = result.fixture
    assert fixture.command == ("python", "bench.py")
    assert fixture.timeout_seconds == 30.0
    assert fixture.working_directory == "bench"
    assert fixture.tags == ("perf", "smoke")
    assert fixture.seed == 42
    assert fixture.parameters == {"size": 1000, "mode": "fast"}
    assert fixture.inputs == ("fixtures/input.json",)
    assert fixture.outputs == ("out/result.bin",)
    assert fixture.metrics_format == "json-last-line"
    assert fixture.assertions[0].metric == "throughput"


def test_fixture_config_rejects_path_traversal(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "[fixture.bad]\n"
        'command = ["true"]\n'
        'inputs = ["../secret"]\n',
    )

    result = load_fixture(tmp_path, "bad")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "invalid_fixture"
    assert "repository" in result.failure.message


def test_fixture_config_rejects_assertion_without_metrics(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "[fixture.bad]\n"
        'command = ["true"]\n'
        "[[fixture.bad.assertions]]\n"
        'metric = "score"\n'
        'operator = ">="\n'
        "value = 1\n",
    )

    result = load_fixture(tmp_path, "bad")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "invalid_fixture"
    assert "metrics_format" in result.failure.message


def test_fixture_config_rejects_nonfinite_parameter(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "[fixture.bad]\n"
        'command = ["true"]\n'
        "[fixture.bad.parameters]\n"
        "ratio = nan\n",
    )

    result = load_fixture(tmp_path, "bad")

    assert not result.ok
    assert result.failure is not None
    assert "finite scalar" in result.failure.message


def test_fixture_not_found_is_distinct(tmp_path: Path) -> None:
    result = load_fixture(tmp_path, "missing")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "fixture_not_found"
