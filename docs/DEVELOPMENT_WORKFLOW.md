# Autonomous Development Workflow

This repository is intentionally structured so an implementation agent can take a ready issue through completion without another planning conversation.

## Required issue lifecycle

For every implementation issue:

1. Read the entire issue and every canonical document required by `docs/RAG_INDEX.md`.
2. Inspect current `main`, open PRs, and issue dependencies before coding. Do not reimplement already-landed work.
3. Create a focused feature branch from current `main`.
4. Implement the smallest coherent solution satisfying the issue and canonical contracts.
5. Update tests and canonical documentation in the same branch whenever behaviour/contracts change.
6. Run the relevant local checks before opening the PR.
7. Commit coherent changes with descriptive messages and push the branch.
8. Open a non-draft PR referencing the issue, with summary, design notes, tests/evidence, known limitations, and `Closes #<issue>` when appropriate.
9. Observe the actual automated checks for the PR. Do not equate “workflow started” with “passed.”
10. If a required automated check fails, inspect logs, fix the underlying cause on the same branch, push, and re-check. Do not merge red CI.
11. Review the final diff for accidental scope growth, secrets, debug files, stale docs, and untested contract changes.
12. After all required automated checks pass, **merge the PR without waiting for additional human approval unless GitHub branch protection or an explicit repository rule requires it.** The issue prompt grants self-merge authority for its scoped work.
13. Verify the PR is actually merged and the target branch contains the merge result.
14. Reconcile the issue: ensure it is closed by the merge or close it as completed, and leave a concise final comment only if useful information is not already in the PR.

Do not stop merely because a PR exists. PR creation is an intermediate state.

## Dependency discipline

If an issue depends on an earlier issue/contract that is not merged, do not merge the dependent implementation against a speculative interface. You may perform analysis or prepare a branch if useful, but completion waits for the dependency unless the issue explicitly allows co-development.

## Automated checks

Phase 0 creates the main code CI. Before Phase 0 lands, the repository may have only planning/document checks. The foundation issue must establish the durable automated checks used by subsequent implementation PRs.

Expected durable checks should cover at least:
- unit tests;
- lint/static checks;
- type checks if the chosen implementation uses them;
- package/CLI smoke test;
- documentation/config fixtures where relevant.

Integration tests that require a live billable Codespace must not run on every ordinary PR unless explicitly configured and safe. Mock/stub GitHub CLI in routine CI; maintain a documented opt-in integration path.

## Testing philosophy

Test contracts and failure paths, not just happy-path command construction. Important cases include:
- malformed config;
- missing `gh`;
- authentication/control-plane error mapping;
- zero/one/multiple workspace candidates;
- remote timeout vs remote non-zero exit;
- JSON stdout validity;
- secret redaction/avoidance;
- checkpoint corruption/mismatch;
- required vs optional verification failure.

## Pull request review checklist

Before merge, the implementing agent must inspect:
- changed-file list;
- full diff;
- automated-check results and relevant logs;
- test coverage of new domain behaviour;
- docs affected by contract changes;
- whether the issue acceptance criteria are demonstrably satisfied.

Do not approve your own reasoning merely because tests are green. Green tests are necessary evidence, not proof that scope/contract is correct.

## Merge method

Prefer squash merge for focused single-issue PRs unless preserving commit structure materially helps. Use repository-supported merge methods. Do not force-push `main`.

## Documentation reconciliation

Canonical docs are executable institutional memory for later agents. If implementation discovers a platform limitation, changed flag, transport constraint, or better contract, update the relevant document and `docs/DECISIONS.md` in the same PR.

## Blocking conditions

An autonomous issue may stop without merge only for a real external blocker, for example:
- required permission/authentication is unavailable;
- GitHub service/control-plane failure persists;
- branch protection requires a human reviewer that cannot be supplied;
- the issue is invalidated by an already-merged conflicting design and safe reconciliation cannot be inferred.

When blocked, leave the branch/PR in a recoverable state and record exactly what remains. Do not claim completion.
