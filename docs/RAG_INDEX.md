# RAG Index and Authority Map

This file is the retrieval entrypoint for implementation agents. Do not treat issue text as the only source of truth when an issue references repository documentation.

## Authority order

When instructions conflict, use this order unless a newer decision explicitly supersedes an older one:

1. The current GitHub issue being implemented, for issue-specific scope and acceptance criteria.
2. `docs/DECISIONS.md`, for explicit programme decisions and supersessions.
3. `docs/ARCHITECTURE.md`, for component boundaries and invariants.
4. `docs/EXECUTION_CONTRACT.md`, for CLI/process/JSON behaviour.
5. `docs/DEVELOPMENT_WORKFLOW.md`, for implementation, verification, PR, merge, and reconciliation procedure.
6. `docs/TOOL_CATALOG.md`, for tool responsibilities and non-goals.
7. `docs/ROADMAP.md`, for sequencing and dependency intent.
8. `README.md`, for orientation only.

If ambiguity remains and safe progress is possible, choose the smallest reversible implementation consistent with the higher-authority documents and record the decision in the PR. Do not broaden scope merely because adjacent functionality is attractive.

## Required retrieval by work type

### Every implementation issue
Read:
- this file;
- the complete issue body;
- `docs/PROGRAMME.md`;
- `docs/ARCHITECTURE.md`;
- `docs/EXECUTION_CONTRACT.md`;
- `docs/DEVELOPMENT_WORKFLOW.md`;
- `docs/DECISIONS.md`;
- the relevant tool section in `docs/TOOL_CATALOG.md`;
- the relevant phase/dependency section in `docs/ROADMAP.md`.

### Workspace lifecycle work
Also read `docs/CODESPACES_GROUND_TRUTH.md`.

### Checkpoint/resume work
Also read `docs/CHECKPOINT_RESUME.md`.

### Verification, fixture, evidence, or matrix work
Also read `docs/VERIFICATION_EVIDENCE.md`.

## Programme vocabulary

- **controller**: the local/client-side `cospaces` process invoking GitHub CLI and coordinating operations.
- **workspace**: a GitHub Codespace selected for a repository/ref/task.
- **remote command**: a non-interactive command executed inside the workspace.
- **run result**: the structured record of one remote command attempt.
- **checkpoint**: durable task state sufficient for a later agent/session to continue intentionally.
- **verification plan**: repository-declared checks whose results can be represented structurally.
- **evidence bundle**: a provenance-bearing set of logs/results/artifacts for a run or verification.
- **fixture**: a declarative reproducible experiment or benchmark.
- **matrix**: repeated comparable execution over explicit dimensions such as refs, configurations, or machine profiles.

## Eight-tool programme

### MVP tranche — implement first
1. `workspace`
2. `run`
3. `checkpoint`
4. `verify`

These four prove the complete minimum loop: acquire a prepared environment, execute work, survive interruption, and determine whether the result is acceptable.

### Second tranche — planned, not required for v0.1
5. `capabilities`
6. `fixture`
7. `evidence`
8. `matrix`

These add richer environment truth, experiment reproducibility, evidence packaging, and comparative execution after the basic loop is reliable.

## Agent operating rule

Issues in this repository are designed as autonomous execution prompts. When assigned an implementation issue, continue through implementation, local/test verification, documentation updates, commit, PR creation, automated-check observation, fixes if necessary, merge when the required checks pass and repository policy permits it, and issue reconciliation/closure. Do not stop at code generation or PR creation unless blocked by an external condition that cannot be resolved from the repository or GitHub state.

## Change discipline

When implementation changes a documented contract, update the canonical document in the same PR. Do not allow code, tests, issue text, and RAG documentation to silently diverge.
