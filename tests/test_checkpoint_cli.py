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

    show_status = main(["checkpoint", "show", "--task", "issue-4", "--root", root, "--json"])
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


def test_invalid_task_id_is_structured_usage_failure(tmp_path, capsys) -> None:
    status = main(
        [
            "checkpoint",
            "show",
            "--task",
            "../escape",
            "--root",
            str(tmp_path),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 2
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_task_id"


def test_malformed_checkpoint_is_structured_persistence_failure(tmp_path, capsys) -> None:
    directory = tmp_path / ".cospaces" / "checkpoints"
    directory.mkdir(parents=True)
    (directory / "issue-4.json").write_text("{broken", encoding="utf-8")

    status = main(
        [
            "checkpoint",
            "validate",
            "--task",
            "issue-4",
            "--root",
            str(tmp_path),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 6
    assert captured.err == ""
    assert payload["ok"] is False
    assert payload["error"]["code"] == "checkpoint_malformed"
