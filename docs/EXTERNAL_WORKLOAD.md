# External Qualification Workload

`cospaces` exposes a bounded repository-owned workload for use by external host qualification programmes. This is **not** a ninth `cospaces` product tool and does not perform remote access, scheduling, billing, or host-specific evidence management.

The contract exists so another system can clone a known `cospaces` commit, install its normal development dependencies, and then execute a stable warm workload whose definition lives with the code being measured.

## Boundary

`cospaces` owns:

- workload stage definitions;
- local execution order;
- stage timeouts;
- bounded diagnostics;
- source/environment/timing metadata;
- machine-readable result schema.

The external orchestrator owns:

- choosing and accessing the host;
- measuring clone/download/install separately when desired;
- selecting the exact `cospaces` commit/ref;
- scheduling repetitions over longer periods;
- provider quota/fair-use policy;
- evidence retention/redaction beyond the runner's bounded output;
- interpretation and classification of the host.

No host/provider names or credentials belong in this repository-owned workload.

## Setup

A typical external host setup is:

```bash
git clone --depth 1 https://github.com/techrote/cospaces.git
cd cospaces
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Clone and dependency installation may use network access and should be measured separately if cold-start performance matters. After setup, the workload profiles themselves require no package-network access. Package build stages use `python -m build --no-isolation`.

For reproducible comparison, pin the clone to an exact commit and retain the emitted `source.commit` value with the external evidence.

## Runner

```bash
python tools/external_workload.py --profile core --json
```

Machine output schema is exactly:

```text
cospaces.external-workload/v1
```

`--json` writes one JSON document to stdout and no successful stage logs.

## Profiles

### `smoke`

Cheap contract/import check:

```text
python -m cospaces --help
```

This is intended for CI and preflight, not useful performance qualification by itself.

### `core` — recommended representative workload

Runs, in order:

1. `python tools/hardening_smoke.py --json`
2. `python -m build --no-isolation --outdir <scratch>/build`

This exercises Python process startup, repository traversal, pytest-heavy contract work, filesystem metadata, JSON processing, package construction, and short-lived subprocesses. It is deliberately bounded and is the preferred external qualification profile.

### `full`

Runs the project CI-like quality stack:

1. Ruff lint;
2. Ruff formatting check;
3. strict mypy;
4. pytest;
5. Phase 1 hardening suite;
6. isolated-output package build without build isolation;
7. module CLI help;
8. installed console CLI help.

Use this when a heavier but still finite repository-development workload is useful. It duplicates some test work by design because the normal project CI does too.

## Repetitions and intervals

Defaults are intentionally conservative:

```bash
python tools/external_workload.py --profile core --repetitions 1 --json
```

A short variance sample can use:

```bash
python tools/external_workload.py \
  --profile core \
  --repetitions 3 \
  --interval-seconds 30 \
  --json
```

Bounds:

- repetitions: `1..24`;
- interval: `0..3600` seconds;
- per-stage timeout: `(0..3600]` seconds;
- default per-stage timeout: 900 seconds.

Longer 24–48 hour sampling should normally be scheduled by the external orchestrator as separate invocations rather than keeping this process alive indefinitely.

## Scratch and cleanup

Each repetition creates one uniquely named temporary directory with prefix:

```text
cospaces-external-workload-
```

Stage stdout/stderr and build artifacts live only inside that directory and are removed automatically when the repetition ends. `--scratch-parent PATH` may place these generated directories beneath an explicit existing directory. The runner never recursively deletes a caller-supplied directory itself.

## Output and privacy

Successful stages report:

- normalized command tokens;
- return status;
- wall time;
- aggregate child user/system CPU time when the platform exposes it;
- stdout/stderr byte counts;
- timeout/launch state.

Successful stdout/stderr content is **not** copied into the result.

On failure, the runner includes only bounded output tails: at most 4 KiB from stdout and 4 KiB from stderr. It records whether either diagnostic tail was truncated.

The environment record contains only:

- Python version/implementation;
- operating-system name/release;
- machine architecture;
- visible CPU count.

It does not serialize environment variables, hostname, username, home directory, executable path, Git remote URL, credentials, or arbitrary file names.

The source record includes only the local Git commit and a dirty boolean.

## Context measurements

Each repetition records, where available:

- start/end UTC timestamps;
- total duration;
- load average before and after;
- free filesystem bytes before and after;
- stage wall and child CPU times.

These are observations of the host visible to the process. They are not claims about dedicated CPU/RAM entitlement on shared infrastructure.

## Dry-run contract check

External tooling can inspect the exact planned stages without running them:

```bash
python tools/external_workload.py --profile core --dry-run --json
```

The plan uses normalized placeholders such as `python` and `<scratch>/build`, so evidence does not leak local user paths.

## Exit status

- `0`: all requested workload stages completed successfully, or dry-run succeeded;
- `1`: a required stage failed, timed out, or could not launch;
- `2`: runner arguments failed bounded validation.

Execution stops at the first failing stage to avoid adding load after the workload is already invalid.

## Interpretation

This workload measures how well a host performs a real `cospaces` development/validation task. It is not a synthetic CPU benchmark and should not be used as a universal machine ranking. External programmes should combine it with workload-specific storage/network/availability evidence and report variance rather than only the fastest run.
