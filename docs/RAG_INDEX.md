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
8. `docs/HARDENING.md`, for current hardening evidence/status and pending live-smoke evidence debt.
9. `docs/EXTERNAL_WORKLOAD.md`, for the repository-owned portable host-qualification workload contract.
10. `docs/ISSUE_ATLAS.md`, for issue-number navigation only.
11. `README.md`, for orientation only.

If ambiguity remains and safe progress is possible, choose the smallest reversible implementation consistent with the higher-authority documents and record the decision in the PR. Do not broaden scope merely because adjacent functionality is attractive.

## Required retrieval by work type

### Every implementation issue
Read this file, the complete issue body, `PROGRAMME`, `ARCHITECTURE`, `EXECUTION_CONTRACT`, `DEVELOPMENT_WORKFLOW`, `AUTONOMOUS_ISSUE_PROMPT`, `DECISIONS`, `ISSUE_ATLAS`, the relevant `TOOL_CATALOG` section, and the relevant `ROADMAP` phase.

### Workspace lifecycle work
Also read `docs/CODESPACES_GROUND_TRUTH.md`.

### Checkpoint/resume work
Also read `docs/CHECKPOINT_RESUME.md`.

### Verification, fixture, evidence, or matrix work
Also read `docs/VERIFICATION_EVIDENCE.md`.

### Phase 1 hardening or Phase 2 activation work
Also read `docs/HARDENING.md`. D026 activates T5 → T6 → T7 while the live Codespace smoke remains pending evidence debt; never infer that smoke passed merely because CI is green.

### External workload / foreign-host qualification work
Also read `docs/EXTERNAL_WORKLOAD.md`. External orchestrators own host access, scheduling, provider policy and evidence interpretation; `cospaces` owns only its repository-local bounded workload definition and result contract.

## Programme vocabulary

- **controller**: the local/client-side `cospaces` process invoking GitHub CLI and coordinating operations.
- **workspace**: a GitHub Codespace selected for a repository/ref/task.
- **remote command**: a non-interactive task executed inside the workspace.
- **run result**: the structured record of one remote task attempt.
- **checkpoint**: durable task state sufficient for a later agent/session to continue intentionally.
- **verification plan**: repository-declared checks whose results can be represented structurally.
- **capability observation**: a live T5 fact with explicit `present`, `absent`, `unavailable`, or `unknown` state.
- **fixture**: a declarative reproducible experiment or benchmark.
- **evidence bundle**: a provenance-bearing, allowlisted package of selected records/artifacts.
- **matrix**: repeated comparable execution over explicit dimensions such as refs, configurations, or machine profiles.
- **external workload**: repository-owned bounded warm workload exposed by `tools/external_workload.py`; it is supporting machinery, not one of the eight tools.

## Eight-tool programme

### Implemented MVP
1. `workspace`
2. `run`
3. `checkpoint`
4. `verify`

### Activated Phase 2 sequence
5. `capabilities` — implementing/land before T6
6. `fixture` — activated next
7. `evidence` — activated after T6

### Deferred
8. `matrix`

D026 is the controlling activation decision. The pending live smoke and #22 remain explicit evidence/hardening debt rather than being silently treated as resolved.

## Agent operating rule

Issues in this repository are designed as autonomous execution prompts. When assigned an implementation issue, continue through implementation, test verification, documentation updates, PR creation, automated-check observation, fixes if necessary, merge when required checks pass and repository policy permits it, and issue reconciliation/closure. Do not stop at code generation or PR creation unless blocked by an external condition that cannot be resolved from repository/GitHub state.

## Change discipline

When implementation changes a documented contract, update the canonical document in the same PR. Do not allow code, tests, issue text, and RAG documentation to silently diverge.
