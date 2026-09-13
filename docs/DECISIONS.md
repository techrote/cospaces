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
