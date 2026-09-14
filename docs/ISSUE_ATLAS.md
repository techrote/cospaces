# Issue Atlas

This is a navigation aid. Issue bodies and canonical contract documents remain authoritative according to `docs/RAG_INDEX.md`.

## Execution sequence

| Issue | Programme item | Tranche | Dependency intent | State intent |
|---|---|---|---|---|
| #1 | Phase 0 package/CI foundation | Foundation | none | complete |
| #2 | T1 `workspace` | MVP | #1 | complete |
| #3 | T2 `run` | MVP | #2 | complete |
| #4 | T3 `checkpoint` | MVP | #2; consume #3 when landed | complete |
| #5 | T4 `verify` | MVP | #3 + #4 | complete |
| #18 | Phase 1 hardening gate | Hardening | #1–#5 | automated hardening complete; live smoke pending |
| #20 | Repository-wide MVP audit/corrective hardening | Hardening | #1–#5 + #18 | complete with PR #21 |
| #22 | Bound T2 output + local timeout cleanup | Hardening debt | T2 + #20 | open follow-up |
| #23 | Portable external qualification workload | Supporting machinery | stable repository quality stack | complete with PR #24 |
| #6 | T5 `capabilities` | Phase 2 | stable T1/T2 + D026 activation | complete with PR #28 |
| #7 | T6 `fixture` | Phase 2 | T5 merged; stable T1/T2/T4 | complete with PR #29 |
| #8 | T7 `evidence` | Phase 2 | stable result/checkpoint records + landed T6 | complete with PR #30 |
| #31 | T5–T7 status-document reconciliation | Reconciliation | merged #28–#30 | complete with PR #32 |
| #9 | T8 `matrix` | Phase 2 | T1/T2 + T6; T7 optional | deferred |

## Current programme boundary

T1–T7 are implemented and merged. The D026 T5 → T6 → T7 sequence is complete. T7's concrete local evidence-bundle contract lives in `docs/EVIDENCE_BUNDLES.md`.

The real disposable-Codespace smoke remains pending evidence debt: it did not block T5–T7, is not considered passed, and cannot be cited as observed live behavior. Issue #22 remains independent hardening debt around T2 output/process-tree resource handling.

No further product tool is currently activated. T8/#9 remains deferred unless separately activated.

## Autonomous completion rule

Every issue contains or incorporates the full autonomous execution mandate. The expected terminal state for a ready implementation issue is:

```text
implemented -> verified -> PR opened -> automated checks green -> PR merged -> merge verified -> issue reconciled/closed
```

External blockers may interrupt this only as described in `docs/DEVELOPMENT_WORKFLOW.md`.

## Drift control

When issue numbers, sequencing, or dependencies change, update this atlas and `docs/ROADMAP.md` in the same reconciliation change. Do not duplicate detailed acceptance criteria here; keep those in the issue and tool contract docs.
