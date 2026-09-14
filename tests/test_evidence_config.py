from pathlib import Path

from cospaces.evidence_config import load_evidence_plan


def test_evidence_plan_parses_bounded_items(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[evidence.default]\n"
        'capture_root = "capture"\n'
        'output_directory = "bundles"\n'
        "max_total_bytes = 1000000\n"
        'notes = ["fixture result plus artifact"]\n'
        "[[evidence.default.items]]\n"
        'path = "fixture.json"\n'
        'kind = "fixture"\n'
        "required = true\n"
        "max_bytes = 100000\n"
        "[[evidence.default.items]]\n"
        'path = "optional.log"\n'
        'kind = "log"\n'
        "required = false\n",
        encoding="utf-8",
    )

    result = load_evidence_plan(tmp_path, "default")

    assert result.ok
    assert result.plan is not None
    assert result.plan.capture_root == "capture"
    assert result.plan.output_directory == "bundles"
    assert result.plan.max_total_bytes == 1_000_000
    assert result.plan.notes == ("fixture result plus artifact",)
    assert result.plan.items[0].kind == "fixture"
    assert result.plan.items[0].max_bytes == 100_000
    assert result.plan.items[1].required is False


def test_evidence_plan_rejects_path_traversal(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        '[evidence.default]\n[[evidence.default.items]]\npath = "../secret"\nkind = "artifact"\n',
        encoding="utf-8",
    )

    result = load_evidence_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "invalid_evidence_plan"


def test_evidence_plan_rejects_oversized_limits(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[evidence.default]\n"
        "max_total_bytes = 999999999999\n"
        "[[evidence.default.items]]\n"
        'path = "file.bin"\n'
        'kind = "artifact"\n',
        encoding="utf-8",
    )

    result = load_evidence_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert "max_total_bytes" in result.failure.message


def test_evidence_plan_not_found_is_distinct(tmp_path: Path) -> None:
    result = load_evidence_plan(tmp_path, "missing")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "evidence_plan_not_found"
