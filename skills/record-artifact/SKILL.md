---
name: record-artifact
description: Capture intermediate outputs (debate rationales, benchmarks, analyses, sketches, reference files) into a thread. Default mode writes each input as a separate file under project-brain/threads/<slug>/artifacts/ (markdown, indexed) or attachments/ (raw/binary), with a breadcrumb line appended to transcript.md. Append mode writes content directly into transcript.md under a timestamped header. Use when the user says "log this", "save this as an artifact", "record the debate result", "attach this file to the thread", "add this to the transcript".
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:<brain>/threads/<slug>/"
  - "write:<brain>/threads/<slug>/"
---

# record-artifact

Captures intermediate outputs into a thread without forcing the user to decide where each file goes. Structured markdown products — rationales, analyses, benchmark tables — become indexed artifacts under `threads/<slug>/artifacts/` with enforced frontmatter. Raw files (PDFs, CSVs, screenshots) become attachments under `threads/<slug>/attachments/` with no frontmatter contract. transcript.md always gets a one-line breadcrumb so the chronological tape still points at every product. Append mode skips the separate file entirely and writes straight into transcript.md — use it when the content really is a running note, not a product.

This is the "grow the thread" skill. `new-thread` creates the container; `record-artifact` fills it with evidence.

## When to invoke

- "Log the debate result" / "save this rationale"
- "Record the benchmark output"
- "Attach this PDF / screenshot / CSV to the thread"
- "Add this as a debate artifact"
- "Append this to the transcript" (→ append mode)
- Any time the user produces output in a conversation worth keeping but doesn't want it inlined in thread.md

## Inputs

| Name                    | Source                                 | Required | Description |
|-------------------------|----------------------------------------|----------|-------------|
| `slug`                  | cwd inference or user prompt           | yes      | Target thread slug; must exist under `threads/` or `archive/`. |
| `title`                 | user prompt                            | yes      | H1 for the new artifact file + label used in the transcript breadcrumb. |
| one of `file` / `content` / `stdin` | user prompt              | yes      | Body source. `file` supports multiple (`--file a --file b`); each becomes its own artifact/attachment. `content` = inline markdown; `stdin` = pipe. |
| `artifact_kind`         | user prompt or inferred                | no       | Free-form label stored in frontmatter. Common values: `debate`, `analysis`, `benchmark`, `sketch`, `reference`, `other`. Default: `artifact`. Used by `review-thread` for grouping. |
| `--append`              | flag                                   | no       | Skip the separate file; append content directly into `transcript.md` under a timestamped H2. Use for short running notes. |
| `by`                    | `--by <email>` flag                    | no       | Actor email. Default: `TODO@example.com` placeholder with a replace-when-ready hint printed by the script. |
| `--brain=<path>`        | cwd inference                          | no       | Absolute path to the brain. Defaults to the nearest ancestor containing `CONVENTIONS.md`. |

Prompt strategy: ask for `title` and body source in one `AskUserQuestion` call if not already obvious from the conversation. Infer `slug` from cwd (the thread dir the user is working in); fall back to asking only if ambiguous. Infer `artifact_kind` from context — e.g., if the user just said "log the debate result", pass `--artifact-kind=debate` without prompting.

## Preconditions

1. A brain root exists (a directory containing `CONVENTIONS.md`) reachable via cwd or `--brain=`.
2. `threads/<slug>/` (or `archive/<slug>/`) exists. The script refuses otherwise — `record-artifact` does not implicitly create threads.
3. Exactly one body source is provided (`--file`, `--content`, or `--stdin`). The script refuses if zero or more than one is set.
4. In default (non-`--append`) mode, each `--file` path exists and is readable.

The script routes markdown inputs to `artifacts/` (frontmatter is injected, V-06 applies) and non-markdown inputs to `attachments/` (V-06 exempt). That routing happens automatically; skills don't pick the destination.

## Process

> ### ⛔️ HARD CONSTRAINT — ONE TOOL CALL
>
> **Call `${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh` ONCE.** No `mkdir`, no `Write` of artifact files, no `Edit` of transcript.md, no `verify-tree` call. The script routes markdown to `artifacts/` (with frontmatter injected), non-markdown to `attachments/`, always appends a transcript breadcrumb, and validates.
>
> **Derive title, slug, and artifact_kind from context:**
> - `--slug` from cwd (nearest `threads/<slug>/` ancestor)
> - `--title` from the user's own framing ("log the debate result" + the content → "JWT vs session rationale")
> - `--artifact-kind` from language: "debate result" → `debate`, "benchmark output" → `benchmark`, "analysis" → `analysis`. Default `artifact` if nothing obvious.
>
> Only use `AskUserQuestion` if slug OR title genuinely can't be inferred.

**Default mode** (new separate file):

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh" \
  --brain=<absolute brain path> \
  --slug=<thread-slug>          \
  --title='<title>'             \
  --content='<markdown body>'   \    # or --file=<path> [--file=<path>]... or --stdin
  [--artifact-kind=<label>]     \
  [--by=<email>]
```

**Append mode** (straight into transcript.md, no separate file):

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh" \
  --brain=<absolute brain path> \
  --slug=<thread-slug>          \
  --title='<title>'             \
  --content='<text>'            \
  --append                      \
  [--by=<email>]
```

After success, passthrough stdout verbatim. If the script exits 1 citing post-write validation errors, tell the user to run `verify-tree` for specifics.

### Dry-run semantics

`record-artifact` does not ship a `--dry-run` flag in rc4 — the write is a single atomic append to transcript.md plus (at most) a handful of file creations under a reserved dir. The script validates inputs up front (thread exists, exactly one body source, file paths readable) so invocation errors fail fast without partial writes.

## Failure modes

- `thread not found` → exit 2. Invoke `discover-threads` or ask the user for the right slug.
- `one of --file, --content, or --stdin is required` / `mutually exclusive` → exit 2. Re-invoke with exactly one source.
- `--file path not found` → exit 2. Fix the path.
- `post-write rebuild reported problems` → exit 1. The artifact is saved but the brain has validation errors — run `verify-tree` to diagnose.

## Postconditions

- At least one file exists under `threads/<slug>/artifacts/` or `threads/<slug>/attachments/` (default mode) OR `transcript.md` gained one entry (append mode).
- `transcript.md` has exactly one new entry regardless of mode.
- In default mode, `thread-index.md` and `current-state.md` reflect the new artifact count.
- `verify-tree --brain <brain>` exits clean.

## Related skills

- **`new-thread`**: creates the thread directory that `record-artifact` fills.
- **`review-thread`**: read-only counterpart; lists artifacts + reads the transcript.
- **`update-thread`**: edits thread.md itself; `record-artifact` never mutates thread.md.
- **`multi-agent-debate`**: for full formal debates with rounds; `record-artifact --artifact-kind=debate` is the lightweight alternative for a simple "we weighed X vs Y" rationale.

## Compatibility

Artifacts stay under the thread after `promote-thread-to-tree` by default — they're thread-scoped history. To carry a specific artifact into `tree/<domain>/<leaf>/`, pass `--promote-artifact=<path>` to `promote-thread-to-tree` (future). Leaves can always soft_link back to thread artifacts using the `threads/<slug>/artifacts/NNNN-<slug>.md` path.

## Changelog

**1.0.0-rc4** — Initial release. Adds the `artifact` kind to the validator (V-01, V-06 apply; new V-22 enforces `source_thread` matches the parent thread dir). Adds `RESERVED_DIRS += artifacts`. `artifact` slot in `REQUIRED_BY_KIND` is `[id, title, kind, created_at, source_thread]`.
