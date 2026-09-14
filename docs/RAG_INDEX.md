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
9. `docs/VERIFICATION_EVIDENCE.md`, for T4/T6 shared verification, fixture, evidence, and matrix semantics.
10. `docs/EVIDENCE_BUNDLES.md`, for the concrete implemented T7 evidence bundle/capture/validation contract.
11. `docs/EXTERNAL_WORKLOAD.md`, for the repository-owned portable host-qualification workload contract.
12. `docs/ISSUE_ATLAS.md`, for issue-number navigation only.
13. `README.md`, for orientation only.

If ambiguity remains and safe progress is possible, choose the smallest reversible implementation consistent with the higher-authority documents and record the decision in the PR. Do not broaden scope merely because adjacent functionality is attractive.

## Required retrieval by work type

### Every implementation issue
Read this file, the complete issue body, `PROGRAMME`, `ARCHITECTURE`, `EXECUTION_CONTRACT`, `DEVELOPMENT_WORKFLOW`, `AUTONOMOUS_ISSUE_PROMPT`, `DECISIONS`, `ISSUE_ATLAS`, the relevant `TOOL_CATALOG` section, and the relevant `ROADMAP` phase.

### Workspace lifecycle work
Also read `docs/CODESPACES_GROUND_TRUTH.md`.

### Checkpoint/resume work
Also read `docs/CHECKPOINT_RESUME.md`.

### Verification, fixture, evidence, or matrix work
Also read `docs/VERIFICATION_EVIDENCE.md`. For T7 evidence work, also read `docs/EVIDENCE_BUNDLES.md`.

### Phase 1 hardening or Phase 2 activation work
Also read `docs/HARDENING.md`. D026 activated T5 → T6 → T7 while the live Codespace smoke remained pending evidence debt; T5–T7 are now implemented. Never infer that the live smoke passed merely because CI is green.

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
- **fixture**: a repository-declared reproducible T6 experiment/benchmark bound to a definition digest and observed remote HEAD.
- **evidence bundle**: a local, provenance-bearing, allowlisted T7 package of selected records/artifacts with captured-byte hashes and independent validation.
- **matrix**: repeated comparable execution over explicit dimensions such as refs, configurations, or machine profiles.
- **external workload**: repository-owned bounded warm workload exposed by `tools/external_workload.py`; supporting machinery, not one of the eight tools.

## Eight-tool programme

### Implemented
1. `workspace`
2. `run`
3. `checkpoint`
4. `verify`
5. `capabilities`
6. `fixture`
7. `evidence`

### Deferred
8. `matrix`

D026 is the controlling activation decision for the completed T5–T7 sequence. The real Codespace smoke remains pending evidence debt and issue #22 remains open T2 hardening debt; neither is silently treated as resolved. T8/#9 requires a separate activation decision.

## Agent operating rule

Issues in this repository are designed as autonomous execution prompts. Continue through implementation, test verification, documentation updates, PR creation, automated-check observation, fixes, merge when checks pass, and issue reconciliation/closure. Do not stop at code generation or PR creation unless blocked by an external condition that cannot be resolved from repository/GitHub state.

## Change discipline

When implementation changes a documented contract, update the canonical document in the same PR. Do not allow code, tests, issue text, and RAG documentation to silently diverge.
