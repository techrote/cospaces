# cospaces

Task-oriented GitHub Codespaces utilities for long-horizon agentic development.

`cospaces` is intended to turn a repository-specific Codespace into a reproducible remote workbench that an autonomous coding/research agent can understand, operate, checkpoint, verify, and hand off safely.

The programme deliberately starts small: define eight composable utilities, implement four in the first tranche, and keep the execution contract narrow enough to test rigorously.

## Initial implementation tranche

1. **workspace** — select/create/start/stop and describe the task Codespace.
2. **run** — execute non-interactive commands remotely and return structured results.
3. **checkpoint** — persist resumable task state independent of a live process or chat context.
4. **verify** — execute repository-declared checks and emit structured verification results.

## Planned second tranche

5. **capabilities** — report what the current environment can actually do.
6. **fixture** — run reproducible declarative experiments and benchmarks.
7. **evidence** — package logs, metadata, hashes, outputs, and provenance.
8. **matrix** — compare runs across refs/configurations/machine profiles.

## Start here

Agents and contributors should read [`docs/RAG_INDEX.md`](docs/RAG_INDEX.md) first. It defines document authority, retrieval rules, the roadmap, and the autonomous issue execution protocol.

Implementation issues are intended to be executable prompts: an implementation agent should be able to open an issue, retrieve the referenced canonical documents, implement the work, verify it, open a PR, inspect required automated checks, merge the PR when green, and reconcile the issue without another planning conversation.

## Development

The controller package targets Python 3.11+ and currently has no runtime dependencies. Install the pinned development tools with:

```bash
python -m pip install -e ".[dev]"
```

Run the same checks used by CI:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/cospaces
python -m pytest
python -m build
python -m cospaces --help
cospaces --help
```

Repository-local configuration begins at `.cospaces.toml`. The current foundation recognises only `cospaces.schema_version = 1`; unknown keys inside `[cospaces]` are rejected, while other top-level sections are retained as uninterpreted forward-compatible data for later tools.

## T1 workspace utility

`workspace` is the first implemented programme tool. Typical machine-readable operations are:

```bash
cospaces workspace list --repo owner/repo --json
cospaces workspace describe --codespace NAME --json
cospaces workspace ensure --repo owner/repo --ref main --json
cospaces workspace ensure --repo owner/repo --ref main --create --machine MACHINE --json
cospaces workspace create --repo owner/repo --branch main --machine MACHINE --json
cospaces workspace stop --codespace NAME --json
```

Selection is deterministic. An explicit Codespace name is validated against the requested repository/ref. Otherwise `ensure` filters repository candidates and fails on zero or multiple matches. It creates only when `--create` is present. GitHub CLI prompting is disabled, so creation that needs an unresolved machine/devcontainer choice fails instead of opening an interactive selector.

Workspace JSON normalises available GitHub data to `name`, `repository`, `ref`, `state`, `display_name`, and `machine`; unavailable metadata remains null/unknown. Normalised states are `available`, `shutdown`, `starting`, or `unknown`.

The other seven tool names remain routing stubs until their implementation issues land.

### Opt-in live smoke test

Routine CI uses mocked GitHub CLI responses and does not create billable Codespaces. With an already-existing disposable Codespace, read-only smoke checks are:

```bash
cospaces workspace list --repo owner/repo --json
cospaces workspace describe --codespace NAME --json
cospaces workspace ensure --repo owner/repo --codespace NAME --json
```

Creation is intentionally separate because it may incur Codespaces usage. If a disposable live creation test is desired, supply explicit machine/devcontainer choices required by the repository, verify the returned workspace identity, then stop it explicitly with `cospaces workspace stop --codespace NAME --json`. T1 never deletes or rebuilds a workspace automatically.
