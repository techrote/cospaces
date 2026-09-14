import argparse
import json

from cospaces.domain.fixture import FixtureAssertionResult, FixtureRunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.fixture_output import emit_fixture_result
from cospaces.services.fixture_service import FixtureActionResult


def test_fixture_json_uses_result_envelope(capsys) -> None:
    workspace = WorkspaceIdentity(
        name="space-one",
        repository="owner/repo",
        ref="main",
        state="available",
        display_name=None,
        machine="standard",
    )
    record = FixtureRunRecord(
        fixture_run_id="fixture-run",
        fixture="bench",
        definition_digest="a" * 64,
        task_run_id="task-run",
        support_run_ids=("head-run",),
        repository="owner/repo",
        ref="main",
        head="b" * 40,
        workspace=workspace,
        command=("python", "bench.py"),
        working_directory=".",
        tags=("perf",),
        seed=42,
        parameters={"size": 1000},
        inputs=(),
        outputs=(),
        metrics_format="json-last-line",
        metrics={"throughput": 12.5},
        assertions=(
            FixtureAssertionResult(
                metric="throughput",
                operator=">=",
                expected=10,
                actual=12.5,
                passed=True,
            ),
        ),
        started_at="2026-09-14T00:00:00Z",
        finished_at="2026-09-14T00:00:01Z",
        duration_seconds=1.0,
        complete=True,
        passed=True,
    )

    status = emit_fixture_result(
        argparse.Namespace(json_output=True),
        FixtureActionResult(record=record),
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "fixture"
    assert payload["ok"] is True
    assert payload["result"]["schema"] == "cospaces.fixture/v1"
    assert payload["result"]["head"] == "b" * 40
    assert payload["result"]["metrics"] == {"throughput": 12.5}
