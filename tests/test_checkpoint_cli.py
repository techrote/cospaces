import json

from cospaces.cli import main


def test_checkpoint_save_show_list_validate_json_contract(tmp_path, capsys) -> None:
    root = str(tmp_path)

    save_status = main(
        [
            "checkpoint",
            "save",
            "--task",
            "issue-4",
            "--root",
            root,
            "--no-git",
            "--repo",
            "owner/repo",
            "--ref",
            "main",
            "--head",
            "abc123",
            "--current",
            "checkpoint",
            "--next",
            "verify",
            "--last-run-id",
            "run-123",
            "--notes",
            "resume here",
            "--json",
        ]
    )
    save_payload = json.loads(capsys.readouterr().out)
    assert save_status == 0
    assert save_payload["operation"] == "checkpoint.save"
    assert save_payload["ok"] is True
    assert save_payload["result"]["checkpoint"]["task_id"] == "issue-4"
    assert save_payload["result"]["checkpoint"]["records"]["last_run_id"] == "run-123"
    assert save_payload["result"]["source_control_action"] == "none"

    show_status = main(
        ["checkpoint", "show", "--task", "issue-4", "--root", root, "--json"]
    )
    show_payload = json.loads(capsys.readouterr().out)
    assert show_status == 0
    assert show_payload["operation"] == "checkpoint.show"
    assert show_payload["result"]["checkpoint"]["progress"]["next"] == "verify"

    list_status = main(["checkpoint", "list", "--root", root, "--json"])
    list_payload = json.loads(capsys.readouterr().out)
    assert list_status == 0
    assert list_payload["result"]["count"] == 1
    assert list_payload["result"]["checkpoints"][0]["task_id"] == "issue-4"

    validate_status = main(
        ["checkpoint", "validate", "--task", "issue-4", "--root", root, "--json"]
    )
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_status == 0
    assert validate_payload["operation"] == "checkpoint.validate"
    assert validate_payload["result"]["live_checked"] is False
    assert validate_payload["result"]["mismatches"] == []
