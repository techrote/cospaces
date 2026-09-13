# Checkpoint and Resume Contract

Checkpointing is a first-class programme primitive because Codespaces may stop, controller processes may disappear, chats may lose context, and implementation may be handed to another agent.

A checkpoint is **not** a process snapshot, source-control operation, or instruction executor. It is a durable structured continuation record.

## Storage

Current checkpoint:

```text
.cospaces/checkpoints/<task-id>.json
```

One previous valid revision:

```text
.cospaces/checkpoints/.history/<task-id>.json
```

Task IDs are restricted to 1–128 characters matching `[A-Za-z0-9][A-Za-z0-9._-]*`; `.` and `..` are rejected. Path separators/traversal therefore cannot escape the checkpoint directory.

A save performs no commit, push, branch mutation, or other source-control action. Machine output reports `source_control_action = "none"`. The checkpoint may later be committed deliberately, but its existence is never evidence that valuable implementation work is committed or pushed.

## Schema v1

The supported schema is exactly `cospaces.checkpoint/v1`:

```json
{
  "schema": "cospaces.checkpoint/v1",
  "task_id": "issue-17",
  "created_at": "2026-09-13T19:00:00Z",
  "updated_at": "2026-09-13T19:05:00Z",
  "repository": "owner/repo",
  "ref": "feature/issue-17",
  "head": "git-sha-or-null",
  "workspace": {
    "name": "...",
    "repository": "owner/repo",
    "ref": "feature/issue-17",
    "state": "available",
    "display_name": "...",
    "machine": "..."
  },
  "working_tree": {
    "dirty": true,
    "summary": "modified=2;added=0;deleted=0;renamed=0;untracked=1;conflicted=0"
  },
  "progress": {
    "completed": ["..."],
    "current": "...",
    "next": "..."
  },
  "records": {
    "last_run_id": "...",
    "last_verification_id": null,
    "paths": []
  },
  "notes": "bounded continuation note"
}
```

The v1 root object is strict: unknown top-level fields are rejected instead of silently discarded. The nested `workspace`, `working_tree`, `progress`, and `records` objects are also strict about their supported keys. This makes misspellings/schema drift detectable at load time.

`repository`, `ref`, `head`, `workspace`, and `working_tree` may be null when unavailable or deliberately not captured. Workspace objects use the T1 normalized identity shape. T2/T4/T7 data is referenced by ID/path rather than embedding large output.

Bounds are compatibility/security controls:
- notes: at most 4000 characters;
- current/next and working-tree summary: at most 1000 characters each;
- completed items, record IDs/paths, and workspace string fields: at most 500 characters each;
- completed/path lists: at most 100 items.

Timestamps must be timezone-aware ISO-8601 values.

## Save semantics

`checkpoint save`:
1. validates task ID and supplied fields;
2. loads and validates an existing checkpoint if present;
3. captures safe local Git context by default;
4. optionally resolves `--codespace NAME` through T1;
5. constructs a complete v1 document;
6. preserves the current valid document into `.history/<task-id>.json` before an update;
7. writes the new current file via a temporary sibling plus `os.replace`;
8. re-reads and validates the written file;
9. emits structured success/failure.

A malformed or unsupported current checkpoint is **not** silently overwritten. The caller must resolve or deliberately remove/recover it first.

On update, omitted progress/record/note/workspace fields preserve their previous valid values. Fresh Git capture refreshes repository/ref/HEAD/working-tree state unless `--no-git` is supplied. Explicit `--repo`, `--ref`, and `--head` values override captured values.

## Safe repository context

Default local Git capture records only:
- normalized GitHub `owner/repo` when inferable from `origin`;
- symbolic branch/ref when attached;
- HEAD;
- aggregate porcelain counts for modified/added/deleted/renamed/untracked/conflicted files;
- dirty/clean boolean.

It does **not** store filenames, raw remote URLs, environment variables, credential-helper output, `.env` content, GitHub tokens, SSH keys, or arbitrary command output. User-supplied notes and record paths are still caller-controlled content and should not contain secrets.

`--no-git` disables repository capture. In that mode repository/ref/HEAD/working-tree values remain null on a fresh checkpoint unless supplied explicitly, or preserve previous values during an update.

## Workspace identity

`checkpoint save --codespace NAME` uses T1 `workspace describe` semantics to store the normalized identity. It does not create, start, stop, rebuild, or delete a Codespace.

The checkpoint schema accepts only the T1 identity keys:
- `name`;
- `repository`;
- `ref`;
- `state`;
- `display_name`;
- `machine`.

## Resume semantics

The MVP does not automatically execute `progress.next`. Resume means recovering validated continuation context.

A later agent should be able to establish:
- task identity;
- repository/ref/HEAD described by the checkpoint;
- recorded workspace identity;
- whether the working tree was dirty when saved;
- completed/current/next progress;
- references to run/verification/evidence records;
- bounded continuation notes.

`checkpoint show` is passive. `checkpoint validate` validates stored data. `checkpoint validate --live` additionally compares stored repository/ref/HEAD to current Git context and, when the checkpoint contains a workspace, resolves that workspace through T1 and compares stable identity fields. A meaningful mismatch returns `checkpoint_context_mismatch` rather than silently declaring resume success.

Workspace runtime state itself is not treated as a resume mismatch because a valid Codespace may legitimately be stopped or starting between sessions.

## History and recovery

MVP history is deliberately bounded to one prior valid revision at `.history/<task-id>.json`. This is enough to diagnose/recover from an accidental valid overwrite without introducing a database or unbounded history store.

If writing the history copy fails, the current checkpoint is left untouched and save fails. If writing the new current file fails after the history copy succeeds, the old current file remains authoritative and the retained history is still valid.

## Validation failures

Stored-data validation distinguishes at least:
- `checkpoint_not_found`;
- `checkpoint_malformed`;
- `checkpoint_invalid`;
- `unsupported_checkpoint_schema`;
- `checkpoint_task_mismatch`;
- `checkpoint_write_failed` / `checkpoint_read_failed`;
- `invalid_task_id`;
- `checkpoint_context_mismatch` for live context divergence.

Persistence failures use exit category `6`; invocation/task-ID failures use category `2`; live context mismatch uses selection category `4`.

## Security boundary

Never capture full environment dumps, authentication material, SSH keys, credential-helper output, arbitrary `.env` content, filenames from Git status, or unbounded command logs by default. Prefer references to T2/T4/T7 results over embedding their payloads.
