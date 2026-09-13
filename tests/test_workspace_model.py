from cospaces.domain.workspace import workspace_from_payload


def test_workspace_payload_is_normalized() -> None:
    workspace = workspace_from_payload(
        {
            "name": "space-one",
            "repository": "owner/repo",
            "gitStatus": {"ref": "feature"},
            "state": "Available",
            "displayName": "Agent workspace",
            "machineName": "standardLinux32gb",
        }
    )

    assert workspace is not None
    assert workspace.to_dict() == {
        "name": "space-one",
        "repository": "owner/repo",
        "ref": "feature",
        "state": "available",
        "display_name": "Agent workspace",
        "machine": "standardLinux32gb",
    }


def test_workspace_payload_preserves_unknown_metadata_as_null() -> None:
    workspace = workspace_from_payload({"name": "space-one", "state": "Mystery"})

    assert workspace is not None
    assert workspace.repository is None
    assert workspace.ref is None
    assert workspace.display_name is None
    assert workspace.machine is None
    assert workspace.state == "unknown"


def test_workspace_payload_supports_structured_repository_shape() -> None:
    workspace = workspace_from_payload(
        {
            "name": "space-one",
            "repository": {"owner": {"login": "owner"}, "name": "repo"},
        }
    )

    assert workspace is not None
    assert workspace.repository == "owner/repo"


def test_workspace_payload_requires_name() -> None:
    assert workspace_from_payload({"state": "Available"}) is None
