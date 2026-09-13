from cospaces.services.repository_probe import _github_repository, summarize_porcelain


def test_clean_working_tree_summary_contains_only_counts() -> None:
    state = summarize_porcelain("")

    assert state.dirty is False
    assert state.summary == "modified=0;added=0;deleted=0;renamed=0;untracked=0;conflicted=0"


def test_dirty_working_tree_summary_does_not_embed_filenames() -> None:
    state = summarize_porcelain(
        " M secrets.env\nA  src/new.py\n?? private-token.txt\nUU src/conflict.py\n"
    )

    assert state.dirty is True
    assert state.summary == "modified=1;added=1;deleted=0;renamed=0;untracked=1;conflicted=1"
    assert "secrets.env" not in state.summary
    assert "private-token" not in state.summary


def test_github_remote_is_normalized_without_userinfo() -> None:
    assert _github_repository("https://user:credential@github.com/owner/repo.git") == "owner/repo"
    assert _github_repository("git@github.com:owner/repo.git") == "owner/repo"
    assert _github_repository("https://example.com/owner/repo.git") is None
