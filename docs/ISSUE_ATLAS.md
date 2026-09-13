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
| #23 | Portable external qualification workload | Supporting machinery | stable repository quality stack | implementation issue |
| #6 | T5 `capabilities` | Phase 2 | MVP + hardening gate | deferred |
| #7 | T6 `fixture` | Phase 2 | stable T1/T2/T4; T5 optional | deferred |
| #8 | T7 `evidence` | Phase 2 | stable result/checkpoint records; T6 when present | deferred |
| #9 | T8 `matrix` | Phase 2 | T1/T2 + T6; T7 optional | deferred |

## Initial implementation boundary

Issues #1 through #5 established the repository foundation plus exactly four implemented tools:

1. T1 `workspace`
2. T2 `run`
3. T3 `checkpoint`
4. T4 `verify`

Issue #18 established the mandatory post-MVP network-free hardening gate. Issue #20 then performed a repository-wide audit and corrected target-selection uncertainty, remote-provenance overclaiming, verification containment, malformed timeout handling, checkpoint schema strictness, T1 wait bounds, malformed T2 preflight ordering, and live-smoke cwd assumptions.

The real disposable-Codespace smoke remains explicit and must be recorded before the Phase 1 gate is considered fully passed. Issue #22 separately tracks the larger T2 process/output resource-hardening change discovered by the audit; its limitation is documented and does not imply the live gate has passed.

Issue #23 adds repository-support machinery only: `tools/external_workload.py` provides a bounded warm workload that foreign hosts/orchestrators can measure. It is not a ninth product tool and does not activate T6 `fixture`, host access, external scheduling, or provider-specific evidence policy.

Do not activate #6–#9 merely because T1–T4 are implemented or because network-free CI is green. Phase 2 remains deferred while the live hardening evidence is pending unless a later explicit decision changes sequencing.

## Autonomous completion rule

Every issue contains or incorporates the full autonomous execution mandate. The expected terminal state for a ready implementation issue is not “PR opened”; it is:

```text
implemented -> locally verified -> PR opened -> automated checks green -> PR merged -> merge verified -> issue reconciled/closed
```

External blockers may interrupt this only as described in `docs/DEVELOPMENT_WORKFLOW.md`.

## Drift control

When issue numbers, sequencing, or dependencies change, update this atlas and `docs/ROADMAP.md` in the same reconciliation change. Do not duplicate detailed acceptance criteria here; keep those in the issue and tool contract docs.
