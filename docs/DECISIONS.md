# Decision Log

This file records load-bearing programme decisions. New decisions should append entries rather than rewrite history without explanation.

## D001 — Eight tools, four-tool initial implementation

**Decision:** Define eight utilities now, but implement only T1–T4 in the first tranche: `workspace`, `run`, `checkpoint`, `verify`.

**Rationale:** These four prove the complete minimum loop without prematurely expanding into richer orchestration.

**Status:** active.

## D002 — GitHub CLI is the initial Codespaces control plane

**Decision:** Wrap supported `gh codespace` commands for v0.1 rather than implementing Codespaces APIs directly.

**Rationale:** It provides an existing authenticated interface for create/list/view/SSH/stop and keeps the project small. Adapters preserve the option to change later.

**Status:** active.

## D003 — Python 3.11+ initial implementation

**Decision:** Use Python 3.11+ for the controller CLI unless a later issue demonstrates a compelling reason to change.

**Rationale:** Fast implementation, strong subprocess/config/testing libraries, portability across typical developer hosts and Codespaces.

**Status:** active.

## D004 — One CLI, eight coherent tool contracts

**Decision:** Expose the programme through one `cospaces` CLI/package with subcommands. Do not create eight unrelated repositories or binaries.

**Status:** active.

## D005 — Non-interactive automation is mandatory

**Decision:** Autonomous/JSON flows must never fall back to interactive GitHub CLI selectors. Ambiguity is an error unless explicit policy resolves it.

**Status:** active.

## D006 — Machine-readable results are first-class

**Decision:** MVP operations support stable JSON envelopes and distinguish infrastructure/controller errors from remote program failures.

**Status:** active.

## D007 — Checkpoint/resume is first-class, not a late reliability feature

**Decision:** Implement checkpointing before verification and keep durable continuation state independent of a live process/chat.

**Status:** active.

## D008 — Repository-defined verification, not generic judgement

**Decision:** `verify` runs explicit repository-declared checks and aggregates their results. It does not invent what “correct” means for a target project.

**Status:** active.

## D009 — No daemon requirement for v0.1

**Decision:** The core tool must work as ordinary finite CLI invocations. A future service/bridge may call it, but the project will not require a resident agent daemon for the MVP.

**Status:** active.

## D010 — Self-merge after green automated checks

**Decision:** Implementation issues authorize their executing agent to merge its scoped PR after required automated checks pass, unless branch protection or an explicit repo rule requires additional review.

**Rationale:** Issues are intended for autonomous long-horizon execution through reconciliation, not code-generation-only handoff.

**Status:** active.

## D011 — Live Codespace integration tests are opt-in

**Decision:** Routine PR CI uses mocks/stubs for GitHub CLI and remote execution. Real Codespace smoke tests are documented and opt-in unless later cost/security controls justify automatic execution.

**Status:** active.

## D012 — Deferred tools are planned but not speculative dependencies

**Decision:** T5–T8 receive detailed issues now, but T1–T4 must not depend on their implementation. MVP may expose narrow internal hooks needed for later composition, but should not build unused frameworks.

**Status:** active.

## D013 — GitHub CLI prompting is disabled at the adapter boundary

**Decision:** Controller-side GitHub CLI calls set `GH_PROMPT_DISABLED=1`. T1 creation also passes `--default-permissions`; callers must provide explicit machine/devcontainer choices when GitHub cannot select them non-interactively.

**Rationale:** An autonomous task must fail visibly on unresolved creation choices rather than block on, or silently resolve through, an interactive selector. `--default-permissions` avoids an authorization prompt without granting requested additional permissions.

**Status:** active.

## D014 — T2 uses argv-preserving POSIX remote encoding over Codespaces SSH

**Decision:** T2 sends caller argv through `gh codespace ssh` as one POSIX-shell command built from individually quoted arguments and the fixed wrapper `set -- ...; "$@"`. Local controller execution always remains argv-based with `shell=False`.

**Rationale:** SSH remote execution necessarily crosses a remote shell command boundary; the fixed wrapper preserves argument tokenisation without allowing caller strings to become controller-shell syntax.

**Limitations:** SSH status 255 is transport/ambiguous, stderr may mix remote and transport diagnostics, and controller timeout does not prove remote termination.

**Status:** active.

## D015 — T2 refuses GitHub CLI versions affected by the Codespaces SSH advisory

**Decision:** T2 requires GitHub CLI 2.62.0 or newer before live Codespaces SSH execution.

**Rationale:** GitHub's GHSA-p2h2-3vg9-4p87 advisory identifies versions through 2.61.0 as affected by a local command-execution vulnerability in Codespaces SSH/log handling.

**Status:** active.

## D016 — T3 uses one atomic current file plus one bounded prior revision

**Decision:** T3 stores `.cospaces/checkpoints/<task-id>.json` as current state and retains the immediately previous valid revision at `.cospaces/checkpoints/.history/<task-id>.json`. Writes use a temporary sibling, flush/fsync, and `os.replace`; a malformed current checkpoint is never overwritten automatically.

**Rationale:** One retained revision provides practical recovery/diagnosis for long-horizon handoff without introducing a database or unbounded history. Refusing to overwrite corrupt state preserves evidence rather than hiding it.

**Status:** active.

## D017 — T3 captures bounded Git state but never source-control success by implication

**Decision:** Checkpoint save captures repo/ref/HEAD plus aggregate dirty-state counts by default, with no filenames or environment dump. Saving performs no commit or push and machine results explicitly report `source_control_action = "none"`.

**Rationale:** Continuation metadata must reveal whether uncommitted work existed without becoming a secret-bearing log or being mistaken for durable source-control publication.

**Status:** active.

## D018 — T4 composes T2 sequentially and pins one workspace

**Decision:** T4 verification checks execute in declared order through the existing T2 `RunService`. Repository-based selection may resolve the first check's Codespace; every subsequent check in that verification targets the same resolved Codespace name. T4 implements no independent Codespaces/SSH transport.

**Rationale:** Sequential composition preserves deterministic order, lower-layer failure categories, and T2 transport safety while preventing one verification from silently hopping between workspaces.

**Status:** active.

## D019 — T4 records references and bounded outcomes, not duplicated logs or secret values

**Decision:** `cospaces.verify/v1` records each check's T2 `run_id`, exit/timeout/completion/duration/failure metadata, declared argv, working directory, and environment variable **keys**. It does not duplicate T2 stdout/stderr or configured environment values. For v0.1 the stdout JSON result is authoritative; automatic persistent report files are deferred.

**Rationale:** The aggregate must be sufficient for an agent to decide required pass/fail and trace evidence without multiplying potentially sensitive/unbounded output. T3 already provides a durable `last_verification_id` reference.

**Status:** active.

## D020 — Phase 1 hardening is a CI-enforced contract suite, not a fifth tool

**Decision:** The post-MVP hardening gate is implemented as cross-tool tests plus `tools/hardening_smoke.py`, which re-runs the complete network-free T1–T4 test suite and emits one machine-readable hardening record. It is not added to the eight-tool CLI surface.

**Rationale:** Hardening validates the contracts already implemented; presenting it as another product tool would blur the programme boundary and duplicate orchestration concepts.

**Status:** active.

## D021 — Real Codespace hardening evidence requires explicit opt-in

**Decision:** The live hardening harness requires the caller to name an existing Codespace. It has no workspace creation, deletion, or rebuild path; stopping afterward requires an explicit `--stop-after`. Phase 2 remains deferred while the real-Codespace smoke is recorded as pending, unless a later explicit decision supersedes this gate.

**Rationale:** Live smoke may start billable compute. Passing network-free CI is not evidence that real Codespaces behavior has been exercised, and the project must not spend or mutate lifecycle implicitly merely to satisfy a roadmap checkbox.

**Status:** superseded for Phase 2 sequencing by D026; live-evidence requirements remain active.

## D022 — Remote provenance must be observed remotely

**Decision:** A verification/evidence field that purports to identify remote Codespace state must come from remote/workspace evidence. T4 v1 does not currently observe the remote Git commit SHA, so its `head` field is null. Controller-local HEAD must not be copied into a remote result merely because repository/ref strings match.

**Rationale:** A branch may advance, a Codespace may be stale, or the controller checkout may differ despite equal ref names. Fabricated precision is worse than an explicit unknown value.

**Status:** active.

## D023 — Selection and verification containment fail closed under uncertainty

**Decision:** T1 does not claim a unique ref match while any relevant candidate has unknown ref metadata. T4 physically resolves its repository root and configured working directory and rejects targets that escape through symlinks. T4 environment/setup/containment failures are infrastructure failures, not repository assertion failures.

**Rationale:** Autonomous orchestration must not turn missing metadata or path indirection into implicit authority to guess a target or execute outside the declared repository boundary.

**Status:** active.

## D024 — T2 process/output resource hardening remains explicit debt

**Decision:** v0.1 continues to use the standard-library process adapter with captured stdout/stderr. The controller will not claim bounded output or guaranteed descendant/remote termination on timeout until a dedicated adapter hardening change implements and tests those properties.

**Rationale:** Truncating output only after unbounded capture does not solve memory pressure, and killing the direct SSH client does not prove remote termination. The limitation is tracked explicitly rather than papered over.

**Status:** active limitation.

## D025 — External host qualification uses repository-owned warm workload machinery

**Decision:** `tools/external_workload.py` exposes a bounded warm workload with schema `cospaces.external-workload/v1` for measurement by foreign hosts/orchestrators. It is supporting repository machinery, not a ninth product tool and not early implementation of T6 `fixture`.

**Rationale:** The codebase being measured should own the exact workload definition so external qualification can pin a commit and compare like with like. Host access, cold clone/install measurement, scheduling, provider policy, evidence retention and interpretation remain the external orchestrator's responsibility.

**Safety:** Successful stage logs are not embedded in results; stage output is spooled to disposable files, failure diagnostics are bounded, environment variables/hostname/user paths are not serialized, repetitions/timeouts are bounded, and package build uses `--no-isolation` so the warm profile requires no package-network access after dependencies are installed.

**Status:** active.

## D026 — Phase 2 T5–T7 is activated while the live smoke remains pending

**Decision:** The user's explicit instruction on 2026-09-14 to implement T5, then T6, then T7 satisfies the previously documented explicit-waiver path for Phase 2 activation. T5–T7 may therefore proceed in that order without first executing the real disposable-Codespace smoke.

**Rationale:** The remaining live smoke is valuable integration evidence but is not a technical dependency for the network-free implementation and validation contracts of T5–T7. Keeping it as evidence debt preserves truthfulness without unnecessarily blocking independently testable work.

**Boundary:** This does **not** mark the live smoke as passed, waive its evidence requirements, resolve #22, or permit any claim about unobserved live Codespaces behavior. T8 remains deferred unless separately activated.

**Status:** active.

## D027 — T5 separates repository intent from observed capability truth

**Decision:** `cospaces capabilities` emits `cospaces.capabilities/v1` and keeps repository-declared support hints separate from live observations. Live observations use the explicit states `present`, `absent`, `unavailable`, and `unknown`, target one T1-selected workspace, and execute remote probes only through T2.

**Rationale:** Configuration can express intended support but cannot prove environment state. Capability reporting must preserve uncertainty and lower-layer failure information rather than turning missing metadata, probe failure, or version-parse failure into optimistic presence claims.

**Status:** active.

## D028 — T6 fixtures bind reproducibility to observed remote provenance and contained paths

**Decision:** `cospaces fixture` emits `cospaces.fixture/v1`. A fixture definition is canonically SHA-256 digested; before the experiment starts T6 observes the selected Codespace's Git HEAD through T2, then executes the task and any output checks through T2 pinned to that same workspace. Working directory, declared inputs and declared outputs must resolve physically within the remote repository checkout.

**Rationale:** Reproducible experiment results require both a stable definition identity and source provenance actually observed in the execution environment. Lexically relative paths alone are insufficient because symlinks can escape the checkout; T6 therefore applies the same fail-closed physical-containment principle as T4.

**Metrics:** v1 optionally parses a bounded scalar JSON object from the final non-empty stdout line and evaluates repository-declared scalar assertions. Seed and parameters are explicit reproducibility metadata injected as `COSPACES_FIXTURE_*` environment assignments; they are not a secret channel.

**Boundary:** T6 references declared output paths but does not package artifact bytes. T7 owns allowlisted capture/hashing. T6 adds no transport layer and inherits T2's documented #22 output/timeout limitation.

**Status:** active.
