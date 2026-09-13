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

The repository is currently in its planning/bootstrap phase. GitHub issues are intended to be executable prompts: an implementation agent should be able to open an issue, retrieve the referenced canonical documents, implement the work, verify it, open a PR, wait for required automated checks, merge the PR when green, and reconcile the issue without needing another planning conversation.
