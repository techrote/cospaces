# Autonomous Issue Execution Prompt

This document is incorporated by reference into implementation issues.

## Execution mandate

You are implementing one scoped issue in `techrote/cospaces`. Treat this as a repository-native autonomous engineering task, not a request for a plan or code sketch.

Continue through all work required for completion in the current execution context:

1. retrieve/read the issue and every document it references, plus all documents required by `docs/RAG_INDEX.md` for this work type;
2. inspect current `main`, relevant merged/open PRs, and dependency issues so you do not duplicate or regress landed work;
3. reconcile any stale issue wording against higher-authority current canonical docs according to `docs/RAG_INDEX.md`;
4. create a focused branch from current `main`;
5. implement the issue completely, including tests, error paths, documentation/config examples, and migrations/reconciliation required by the change;
6. run the repository's relevant local verification commands;
7. inspect your own final diff and remove debug output, accidental files, secrets, stale docs, and unjustified scope growth;
8. commit and push the branch;
9. open a non-draft PR referencing the issue and describing implementation, design decisions, tests/evidence, and limitations;
10. inspect the actual automated checks for the PR;
11. if a required check fails, inspect logs, correct the cause on the same branch, push, and repeat verification;
12. after required automated checks pass, merge the PR yourself using a repository-supported merge method unless branch protection or an explicit current repository rule requires another reviewer;
13. verify that the PR actually merged and `main` contains the expected result;
14. ensure the issue is closed/reconciled as completed.

Do not stop after producing code, after pushing a branch, or after opening a PR. Those are intermediate states.

## Engineering rules

- Preserve the architectural and safety invariants in `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`.
- Keep GitHub CLI/subprocess behaviour behind test seams; routine CI must not require a live billable Codespace.
- Never rely on interactive GitHub CLI selectors in autonomous paths.
- Avoid shell-string interpolation for local subprocess execution.
- Treat JSON/stdout behaviour and exit-code/error categories as public contracts covered by tests.
- Do not collect or log tokens, SSH private material, credential-helper output, full environment dumps, or `.env` contents.
- Prefer the smallest coherent implementation satisfying the issue; do not build deferred framework features speculatively.
- When implementation changes a contract, update the canonical RAG documentation and `docs/DECISIONS.md` in the same PR.
- If the issue is genuinely blocked by external permissions/service state/required human review, leave a recoverable branch/PR and record the precise blocker. Do not claim completion.

## Evidence standard

The PR must report the commands/checks actually run and their results. Automated CI passing is necessary before self-merge. Where a live Codespace integration test is optional or unavailable, rely on mocked/unit contract tests and clearly state whether an opt-in live smoke test was or was not run.
