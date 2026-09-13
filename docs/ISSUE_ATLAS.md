# Issue Atlas

This is a navigation aid. Issue bodies and canonical contract documents remain authoritative according to `docs/RAG_INDEX.md`.

## Execution sequence

| Issue | Programme item | Tranche | Dependency intent | State intent |
|---|---|---|---|---|
| #1 | Phase 0 package/CI foundation | Foundation | none | implement first |
| #2 | T1 `workspace` | MVP | #1 | initial implementation |
| #3 | T2 `run` | MVP | #2 | initial implementation |
| #4 | T3 `checkpoint` | MVP | #2; consume #3 when landed | initial implementation |
| #5 | T4 `verify` | MVP | #3 + #4 | initial implementation |
| #6 | T5 `capabilities` | Phase 2 | MVP + hardening gate | deferred |
| #7 | T6 `fixture` | Phase 2 | stable T1/T2/T4; T5 optional | deferred |
| #8 | T7 `evidence` | Phase 2 | stable result/checkpoint records; T6 when present | deferred |
| #9 | T8 `matrix` | Phase 2 | T1/T2 + T6; T7 optional | deferred |

## Initial implementation boundary

The intended first execution campaign is **#1 through #5**, which establishes the repository foundation plus exactly four implemented tools:

1. T1 `workspace`
2. T2 `run`
3. T3 `checkpoint`
4. T4 `verify`

After #5, stop and perform the Phase 1 hardening gate described in `docs/ROADMAP.md` before activating #6–#9, unless a later explicit decision changes that sequencing.

## Autonomous completion rule

Every issue contains or incorporates the full autonomous execution mandate. The expected terminal state for a ready implementation issue is not “PR opened”; it is:

```text
implemented -> locally verified -> PR opened -> automated checks green -> PR merged -> merge verified -> issue reconciled/closed
```

External blockers may interrupt this only as described in `docs/DEVELOPMENT_WORKFLOW.md`.

## Drift control

When issue numbers, sequencing, or dependencies change, update this atlas and `docs/ROADMAP.md` in the same reconciliation change. Do not duplicate detailed acceptance criteria here; keep those in the issue and tool contract docs.
