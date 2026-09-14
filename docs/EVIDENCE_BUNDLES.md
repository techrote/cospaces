# T7 Evidence Bundle Contract

T7 `evidence` packages explicitly selected local records and artifacts into a bounded, inspectable directory bundle. It does not SSH into a Codespace, scan a workspace, upload evidence, or infer what should be captured.

## Interface

```bash
cospaces evidence create PLAN --root . --json
cospaces evidence create PLAN --root . --output DIR --json
cospaces evidence validate BUNDLE --root . --json
```

Creation emits `cospaces.evidence/v1` inside the normal `cospaces.result/v1` envelope. Validation emits `cospaces.evidence-validation/v1` inside the same outer result envelope.

## Repository-controlled plan

Plans live in `.cospaces.toml`:

```toml
[evidence.default]
capture_root = "evidence-source"
output_directory = ".cospaces/evidence"
max_total_bytes = 104857600
notes = ["public-safe context only"]

[[evidence.default.items]]
path = "fixture.json"
kind = "fixture"
required = true
max_bytes = 52428800

[[evidence.default.items]]
path = "optional.log"
kind = "log"
required = false
```

Supported item kinds are `artifact`, `checkpoint`, `fixture`, `log`, `other`, `run`, and `verification`. Capture is file-by-file: directories are never recursively archived merely because they were named.

Defaults are deliberately bounded: 50 MiB per item and 100 MiB total. Configuration permits at most 256 items, at most 1 GiB for one item, and at most 2 GiB total; callers should choose materially smaller limits unless larger evidence is genuinely required.

## Capture-root and path boundary

`capture_root`, `output_directory`, and item paths are repository-relative POSIX paths. Absolute paths, `..`, backslashes, NULs, physical escape through symlinks, and broad secret-prone paths are rejected.

Secret-prone path defaults include `.ssh`, `.gnupg`, `.aws`, `.azure`, `.kube`, `.env` / `.env.*`, Git credential files, common private-key filenames, and Git credential/config paths. A safe-looking symlink that physically resolves into one of those paths is rejected as well.

The CLI `--output` override receives the same output-path safety checks as the configured output directory.

## Secret-like content boundary

Before capture, files are scanned in bounded chunks for obvious private-key headers and GitHub token prefixes. Evidence-plan notes are checked for the same obvious token/private-key markers.

This scanner is a conservative safety floor, not a general secret-classification engine. Callers remain responsible for selecting public-safe material; T7 does not promise to discover every possible credential format or sensitive datum.

## Bundle layout

Each creation receives a new UUID evidence ID and creates a fresh directory under the approved output directory:

```text
<output>/<evidence-id>/
  manifest.json
  files/
    0000
    0001
    ...
```

Source filenames are not reused as stored filenames. Indexed generic names keep the bundle layout deterministic and reduce accidental disclosure through filenames.

Creation occurs in a temporary sibling directory and is atomically renamed into the final evidence-ID directory. Existing bundles are never overwritten.

## Captured-file integrity

T7 copies an approved source file into the temporary bundle, then records the copied destination size and SHA-256 digest. The manifest therefore describes the bytes actually placed in the bundle rather than trusting a pre-copy source hash.

Successful capture records:
- item index/kind;
- original relative source path;
- generic stored path;
- required flag and status;
- captured size;
- SHA-256 digest;
- inferred content type;
- recognized record schema and bounded provenance when applicable.

An absent optional item remains visible as `status = "missing_optional"`; an absent required item fails bundle creation.

## Recognized cospaces records

For `checkpoint`, `fixture`, `run`, and `verification` items, T7 parses the captured JSON and validates the expected record shape/schema rather than treating arbitrary JSON as trusted provenance. A normal `cospaces.result/v1` envelope is unwrapped when necessary.

Per-item provenance may include only bounded structural identifiers such as repository/ref/HEAD when present, workspace identity, task/correlation IDs, run/verification/fixture IDs, checkpoint record references, and fixture support-run IDs. T7 does not fabricate a single aggregate repository HEAD when included records legitimately have different or unknown provenance.

## Independent validation

`evidence validate` does not require the original capture plan or source files. It validates the bundle itself:
- supported manifest schema and structure;
- safe relative stored paths;
- no stored-file symlinks or escape from the bundle;
- regular-file existence;
- recorded size and SHA-256 against current captured bytes;
- obvious secret-marker scan on captured bytes;
- optional omissions remain structurally explicit;
- the `files/` set contains exactly the files referenced by the manifest, with no missing or unexpected captured files.

Validation failures use verification exit category `7`; creation/configuration failures retain usage/persistence categories as appropriate.

## Security and non-goals

T7 is intentionally an allowlist packager, not a redacting archival crawler. It does not capture whole workspaces/home directories by default, follow symlinks outside approved roots, back up secrets, host/upload bundles, or prove authenticity against a malicious party.

SHA-256 and independent validation provide bundle integrity checking, not cryptographic signing or external attestation. T8 matrix execution remains a separate deferred tool.
