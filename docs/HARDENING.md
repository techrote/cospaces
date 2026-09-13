# Phase 1 Hardening Gate

This document records the hardening status of the implemented four-tool MVP before deferred Phase 2 tools are activated.

## Current status

- **Automated/network-free hardening:** enforced in ordinary CI through `python tools/hardening_smoke.py --json`.
- **Repository-wide audit (#20 / PR #21):** corrected fail-open selection, false remote provenance, verification symlink containment, non-finite timeout handling, checkpoint schema strictness, T1 controller wait bounds, malformed T2 preflight ordering, and live-smoke cwd assumptions.
- **Real Codespace smoke:** **pending**. It has not been executed because no existing disposable Codespace was explicitly selected for live use.
- **T2 output/process-tree hardening:** tracked separately in #22; current v0.1 capture remains intentionally documented as unbounded at the process-adapter layer.
- **Phase 2 activation:** remains deferred while the real-Codespace smoke is pending, unless a later explicit decision supersedes this gate.

The pending live check is evidence debt, not permission to guess that live GitHub/Codespaces behavior passed.

## Network-free hardening runner

Run:

```bash
python tools/hardening_smoke.py --json
```

The runner executes the complete repository test suite with no live Codespace dependency and emits one `cospaces.hardening/v1` JSON record containing the pytest exit status, duration, and captured output.

The suite includes the existing T1–T4 unit/contract tests plus cross-tool hardening tests for:

- explicit result/checkpoint/verification schema versions;
- stable exit categories 0–7;
- workspace zero/one/multiple selection, unknown-ref uncertainty, and ambiguity behavior;
- bounded T1 control-plane waits;
- T2 transport, timeout, malformed-request preflight, and remote-failure distinctions;
- checkpoint strict-schema, corruption/history/path-safety behavior;
- reconstructed-controller checkpoint continuity;
- preservation of T1 workspace identity, T2 run IDs, and T4 verification IDs across checkpoint handoff;
- passive checkpoint `next` semantics;
- required/optional verification aggregation;
- T4 physical working-directory containment and environment/setup failure classification;
- truthful T4 provenance with unobserved remote HEAD left null;
- real verification parser/config/service/output composition over a fake T2 boundary;
- JSON-only automation output.

Routine CI must remain network-free and must never create a billable Codespace.

## Explicit live smoke harness

A live smoke may be run only when the caller deliberately provides an **existing disposable Codespace**:

```bash
python tools/live_codespace_smoke.py --codespace NAME --checkpoint-root . --json
```

The harness composes the actual T1–T4 service interfaces in this order:

1. describe the named Codespace;
2. run a bounded, cwd-independent `git --version` probe through T2;
3. run a temporary one-check T4 `git status --short` verification from the physically contained repository checkout;
4. save/show/validate a generated T3 checkpoint carrying the T1 workspace identity plus T2/T4 IDs;
5. remove the generated checkpoint by default.

It has no workspace-creation, deletion, or rebuild path. It does **not** search for or choose a Codespace on the caller's behalf. Connecting to/running work in an existing stopped Codespace may start billable compute, so invocation itself is the explicit opt-in boundary.

To stop the named Codespace after the smoke, request it explicitly:

```bash
python tools/live_codespace_smoke.py --codespace NAME --stop-after --json
```

`--stop-after` is never implied. Use `--keep-checkpoint` only when the generated smoke checkpoint should remain for inspection.

## Evidence required to mark the gate passed

Record at least one disposable live run showing:

- T1 describe succeeds for the intended repository/ref;
- T2 remote command succeeds and returns a structured run ID;
- T3 checkpoint stores and returns that run ID and the T1 workspace identity;
- T4 verification establishes the contained repository root, succeeds, and returns a structured verification ID;
- the checkpoint stores the verification ID;
- cleanup/stop behavior matches the explicit caller choice;
- no workspace create/delete/rebuild occurred implicitly.

A failing live smoke should produce a follow-up corrective issue rather than moving Phase 2 forward by assumption.
