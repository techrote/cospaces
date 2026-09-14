import argparse
import json

from cospaces.capabilities_output import emit_capability_result
from cospaces.domain.capabilities import (
    CapabilityObservation,
    CapabilityReport,
    CapabilityState,
)
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.capability_service import CapabilityActionResult


def test_capabilities_json_uses_result_envelope(capsys) -> None:
    workspace = WorkspaceIdentity(
        name="space-one",
        repository="owner/repo",
        ref="main",
        state="available",
        display_name=None,
        machine="standardLinux32gb",
    )
    report = CapabilityReport(
        controller_version="0.0.1",
        github_cli=CapabilityObservation(
            name="github_cli",
            state=CapabilityState.PRESENT,
            version="2.80.0",
        ),
        workspace=workspace,
        declared_support={"build": True},
        observations=(
            CapabilityObservation(
                name="python",
                state=CapabilityState.PRESENT,
                version="3.11.9",
                run_id="run-1",
                command=("python", "--version"),
            ),
        ),
    )
    namespace = argparse.Namespace(json_output=True)

    status = emit_capability_result(namespace, CapabilityActionResult(report=report))

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "capabilities"
    assert payload["ok"] is True
    assert payload["result"]["schema"] == "cospaces.capabilities/v1"
    assert payload["result"]["declared_support"] == {"build": True}
    assert payload["result"]["observations"][0]["state"] == "present"
