# cospaces

Task-oriented GitHub Codespaces utilities for long-horizon agentic development.

`cospaces` is intended to turn a repository-specific Codespace into a reproducible remote workbench that an autonomous coding/research agent can understand, operate, checkpoint, verify, and hand off safely.

The programme deliberately starts small: define eight composable utilities, implement four in the first tranche, and keep the execution contract narrow enough to test rigorously.

## Initial implementation tranche

1. **workspace** — select/create/reuse/stop and describe the task Codespace.
2. **run** — execute non-interactive commands remotely and return structured results.
3. **checkpoint** — persist resumable task state independent of a live process or chat context.
4. **verify** — execute repository-declared checks and emit structured verification results.

## Planned second tranche

5. **capabilities** — report what the current environment can actually do.
6. **fixture** — run reproducible declarative experiments and benchmarks.
7. **evidence** — package logs, metadata, hashes, outputs, and provenance.
8. **matrix** — compare runs across refs/configurations/machine profiles.

## Start here

Agents and contributors should read [`docs/RAG_INDEX.md`](docs/RAG_INDEX.md) first. It defines document authority, retrieval rules, the roadmap, and the autonomous issue execution protocol.

Implementation issues are intended to be executable prompts: an implementation agent should be able to open an issue, retrieve the referenced canonical documents, implement the work, verify it, open a PR, inspect required automated checks, merge the PR when green, and reconcile the issue without another planning conversation.

## Development

The controller package targets Python 3.11+ and currently has no runtime dependencies. Install the pinned development tools with:

```bash
python -m pip install -e ".[dev]"
```

Run the same checks used by CI:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/cospaces
python -m pytest
python tools/hardening_smoke.py --json
python tools/external_workload.py --profile smoke --json
python -m build
python -m cospaces --help
cospaces --help
```

Repository-local configuration lives at `.cospaces.toml`. `[cospaces]` currently accepts only `schema_version = 1`; T4 consumes the separate `[verify.<plan>]` sections described below. Other top-level sections remain reserved for later tools.

## Portable external qualification workload

`cospaces` also exposes a bounded repository-owned **warm workload** for measurement by external hosts/orchestrators. This is supporting repository machinery, not a ninth product tool and not early T6 `fixture` implementation.

After cloning a pinned commit and installing `.[dev]`, the recommended representative workload is:

```bash
python tools/external_workload.py --profile core --json
```

`core` runs the Phase 1 hardening suite followed by a package build using `--no-isolation`, so the warm profile requires no package-network access after dependencies are installed. `smoke` provides a very cheap contract check; `full` runs the broader CI-like quality stack.

The machine schema is `cospaces.external-workload/v1`. It records source commit, bounded platform context, repetition/stage timing, aggregate child CPU time where available, load/free-space context, output byte counts, and bounded failure diagnostics. Successful command output is not embedded. Environment variables, hostname, username, home path and Git remote URL are not serialized.

External systems remain responsible for host access, cold clone/install measurement, longer scheduling, provider limits, evidence retention and interpretation. See [`docs/EXTERNAL_WORKLOAD.md`](docs/EXTERNAL_WORKLOAD.md) for the complete contract and safe repetition examples.

## T1 workspace utility

Typical machine-readable operations are:

```bash
cospaces workspace list --repo owner/repo --json
cospaces workspace describe --codespace NAME --json
cospaces workspace ensure --repo owner/repo --ref main --json
cospaces workspace ensure --repo owner/repo --ref main --create --machine MACHINE --json
cospaces workspace create --repo owner/repo --branch main --machine MACHINE --json
cospaces workspace stop --codespace NAME --json
```

Selection is deterministic and fail-closed. An explicit Codespace name is validated against the requested repository/ref. Otherwise `ensure` filters repository candidates and fails on zero or multiple matches. When a ref is requested, unknown candidate-ref metadata also fails selection if it prevents proving that exactly one candidate matches; a known match is not chosen while another candidate could also match. Creation occurs only when `--create` is present.

GitHub CLI prompting is disabled, so creation that needs an unresolved machine/devcontainer choice fails instead of opening an interactive selector. T1 control-plane calls are controller-time-bounded; a stalled call produces retryable infrastructure failure instead of waiting indefinitely.

Workspace JSON normalises available GitHub data to `name`, `repository`, `ref`, `state`, `display_name`, and `machine`; unavailable metadata remains null/unknown. Normalised states are `available`, `shutdown`, `starting`, or `unknown`.

## T2 run utility

`run` executes one non-interactive argv inside exactly one Codespace. The task boundary after `--` is mandatory:

```bash
cospaces run --codespace NAME -- git status --short
cospaces run --codespace NAME --timeout 2m --json -- python -m pytest -q
cospaces run --repo owner/repo --ref main --json -- python -m pytest -q
cospaces run --codespace NAME --task-id issue-42 --correlation-id agent-pass-3 --json -- git status --short
```

An explicit Codespace is described through T1 before execution. Repository targeting delegates to T1's deterministic repository/ref resolver. T2 never creates a workspace and never retries the remote task implicitly. Invalid/non-finite timeouts and NUL-bearing argv are rejected before workspace lookup or transport work.

JSON records include a unique `run_id`, caller metadata, timeout, observed exit status, timeout state, remote-completion state, duration/timestamps, captured output, workspace identity, and `transport = "gh-codespace-ssh"`. A remote non-zero status exits in category 5; controller/SSH transport failure is category 3; selection failure is category 4.

The SSH transport has deliberate truthfulness limits: status 255 is transport/ambiguous, stderr can contain both remote stderr and SSH diagnostics, and a controller timeout does not prove the remote process stopped. These states are represented explicitly instead of guessed.

Live T2 execution requires GitHub CLI 2.62.0 or newer because earlier versions are affected by GitHub's Codespaces SSH security advisory. The target Codespace must also provide an SSH server.

The controller does not inspect or serialize its credential stores or environment. Task argv/stdout/stderr are caller-selected data and are captured by design, so do not execute commands that print secrets when the resulting run record will be retained or shared.

**Known v0.1 resource limit:** the current process adapter captures stdout/stderr in memory without an output-size bound. Timeout also cannot prove descendant/remote termination. Issue #22 tracks bounded/spooled output and local timeout cleanup; the current contract leaves remote completion `unknown` rather than overstating certainty.

## T3 checkpoint utility

`checkpoint` stores durable continuation metadata under the target repository. It does not snapshot a process, commit code, push branches, or execute the recorded next step.

```bash
cospaces checkpoint save --task issue-42 --current "implement parser" --next "run tests" --last-run-id RUN-ID --json
cospaces checkpoint show --task issue-42 --json
cospaces checkpoint list --json
cospaces checkpoint validate --task issue-42 --json
cospaces checkpoint validate --task issue-42 --live --json
```

Current files live at `.cospaces/checkpoints/<task-id>.json`; one previous valid revision is retained at `.cospaces/checkpoints/.history/<task-id>.json`. Saves use a temporary sibling plus atomic replacement where the host filesystem supports it. A corrupt current checkpoint is never silently overwritten.

`cospaces.checkpoint/v1` is strict: unknown root or supported nested-object fields are rejected rather than silently discarded.

By default `save` captures safe local Git context: normalized GitHub `owner/repo` when inferable, current ref, HEAD, and aggregate working-tree counts. It deliberately does not store filenames. `--no-git` disables that capture. Explicit `--repo`, `--ref`, and `--head` values override captured values.

Progress, note, record-reference, and workspace fields are bounded. Omitted fields preserve the previous valid revision during an update. `--codespace NAME` uses T1 to store the normalized workspace identity; run references such as `--last-run-id` remain references rather than embedded T2 output.

`validate --live` compares stored repo/ref/HEAD with the current repository and, when a workspace identity is present, compares it through T1. A meaningful mismatch is a non-successful validation rather than an automatic "resume". Ordinary `show` and `validate` never execute `progress.next`.

Every save result states `source_control_action = "none"`: a repository-local checkpoint is not evidence that its contents or the implementation itself are committed or pushed.

## T4 verify utility

`verify` runs a named repository-controlled plan through T2, sequentially, in one resolved Codespace:

```bash
cospaces verify default --repo owner/repo --ref main --json
cospaces verify default --codespace NAME --task-id issue-42 --json
```

A minimal `.cospaces.toml` plan is:

```toml
[cospaces]
schema_version = 1

[verify.default]

[[verify.default.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]
timeout_seconds = 600
required = true

[[verify.default.checks]]
name = "lint"
command = ["python", "-m", "ruff", "check", "."]
timeout_seconds = 120
required = false
working_directory = "."
environment = { MODE = "ci" }
```

Commands are argv arrays, not shell strings. Check names are unique inside a plan. Timeouts must be finite. `working_directory` is lexically repository-relative and is then physically resolved in the Codespace; symlinks cannot escape the checkout. Environment overrides must be explicit string values; verification records expose only their keys, not their configured values.

All checks execute in declaration order. The first resolved Codespace is reused for the rest of the plan. A genuine remote failure or timeout in a required check makes the aggregate verification fail with exit category `7`; the verifier still runs later declared checks. Optional failures/timeouts remain visible but do not fail the required aggregate. Configuration errors, workspace selection failures, transport/control-plane failures, and repository-root/containment setup failures retain infrastructure/selection categories rather than being relabelled as failed tests.

Each invocation receives a unique `verification_id`. The `cospaces.verify/v1` record includes plan/task/correlation IDs, repository/ref/workspace provenance where established, timestamps, aggregate `complete`/`passed` flags, and per-check T2 `run_id`, exit/timeout/completion summary, duration and failure code. **T4 v1 does not currently observe the remote Git commit SHA, so `head` is null rather than borrowing the controller checkout HEAD.** T3 can store the verification ID in `records.last_verification_id`.

For v0.1, the JSON result on stdout is authoritative; T4 does not create a persistent report file automatically. It also does not replace code review or invent product-correctness criteria—the repository declares what verification means.

## Phase 1 hardening status

T1–T4 complete the intended first implementation tranche. Issue #18 added a CI-enforced network-free hardening runner, and issue #20/PR #21 performed a repository-wide corrective audit:

```bash
python tools/hardening_smoke.py --json
```

The audit tightened target certainty, provenance truthfulness, physical verification containment, timeout/schema validation, and malformed-request preflight. The larger T2 output/process-tree limitation is tracked separately in #22 rather than being hidden by a partial fix.

The real disposable-Codespace smoke is intentionally **not** automatic and remains pending until an existing disposable Codespace is named explicitly. See [`docs/HARDENING.md`](docs/HARDENING.md). Phase 2 remains deferred while that evidence is pending unless a later explicit decision changes the gate.

## Opt-in live smoke

Routine CI never creates or runs a billable Codespace. To deliberately exercise all four MVP tools against one existing disposable Codespace:

```bash
python tools/live_codespace_smoke.py --codespace NAME --checkpoint-root . --json
```

The harness only operates on the named existing Codespace. It describes it, performs a bounded cwd-independent T2 `git --version` probe, performs one temporary T4 repository-root verification, writes/shows/validates a generated T3 checkpoint, and cleans that checkpoint by default. It contains no create/delete/rebuild path.

Connecting to a stopped Codespace may start billable compute, so invoking the harness is the explicit opt-in boundary. Stopping afterward is also explicit:

```bash
python tools/live_codespace_smoke.py --codespace NAME --stop-after --json
```

Use `--keep-checkpoint` only when the generated smoke checkpoint should remain for inspection.
