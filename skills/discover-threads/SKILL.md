---
name: discover-threads
description: Read-only discovery skill that queries per-thread frontmatter ad-hoc with rich filters (status, assignment, maturity, domain, review requirement, stale-thread detection, PR state) and returns filtered views on demand. Works even if thread-index.md is stale. Supports table, JSON, CSV, YAML, and path-only output formats. Use when the user says "what threads are assigned to me", "what parked threads are blocking promotion", "what stale threads in <some-domain>", "threads requiring two-human review", or needs a machine-readable feed for downstream tooling.
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:[brain-root]"
  - "read:~/.config/project-brain/projects.yaml"
  - Bash (optional; only for PR state checks via gh)
---

# discover-threads

The `verify-tree --rebuild-index` skill regenerates the aggregate `thread-index.md` on every write. But that file is a snapshot, not a live query engine. `discover-threads` is the counterpart: it reads per-thread frontmatter directly, applies rich filters on demand (status, assignment, maturity, domain, stale-thread detection, review policy), and streams results in the format the user needs — table, JSON, CSV, YAML, or plain file paths.

The skill is read-only. It works even when `thread-index.md` and `current-state.md` are stale or missing — the source of truth is always the per-thread files themselves (CONVENTIONS § 1.1). Use this when you need live inventory that is guaranteed to be up-to-date with the current working tree state, or when you need to export thread data to downstream systems (dashboards, CI checks, team tools).

## When to invoke

- "What threads are assigned to me?" / "Show my assignments"
- "What threads are stale?" / "What hasn't been touched in 30 days?"
- "What parked threads are actionable?" / "Show parked threads with unpark_trigger set"
- "What threads in `<domain>/` require two-human review?"
- "What in-review threads have open PRs?" / "Surface PR state for active threads"
- "Export thread inventory to JSON" / "feed a dashboard with live thread list"
- "What threads target a specific tree domain?" / "find all threads aimed at product/billing"
- After `update-thread`, `park-thread`, or other mutations, to verify the result without waiting for index rebuild

## Inputs

All flags are optional and combinable AND-style. If no filters are supplied, all active/parked/in-review threads are returned (archived excluded by default).

| Flag | Type | Example | Semantics |
|------|------|---------|-----------|
| `--status=<list>` | multi-select (comma-separated) | `--status=active,parked` | Thread status: `active`, `parked`, `in-review`, `archived`. Default: `active,parked,in-review`. |
| `--owner=<handle>` | string match | `--owner=alice` | Match `created_by` OR `last_modified_by` containing the handle. |
| `--assigned=<handle>` | string match | `--assigned=tom` | Match any entry in `assigned_to` array containing the handle. Case-insensitive. |
| `--domain=<prefix>` | prefix match | `--domain=engineering/api` | Match `tree_domain` by prefix. Example: `--domain=product` matches `product/billing`, `product/ui`, etc. |
| `--maturity=<list>` | multi-select | `--maturity=locking,refining` | Thread maturity: `exploring`, `refining`, `locking`. Only applies to `active` or `parked` threads (others have no maturity). |
| `--modified-before=<spec>` | relative or ISO-8601 | `--modified-before=30d` or `--modified-before=2026-04-01` | Last modified at or before the given date. Relative format: `<N>d` = N days ago, `<N>h` = N hours ago. ISO: `YYYY-MM-DD` or full ISO-8601 with time. |
| `--modified-after=<spec>` | relative or ISO-8601 | `--modified-after=7d` | Last modified at or after the given date. |
| `--review-requirement=<string>` | exact match | `--review-requirement=two-human` | Exact match on `review_requirement` field (e.g. `"one-human"`, `"two-human"`, `"legal-sign-off"`, `"optional"`). |
| `--has-pr` / `--no-pr` | flag | `--has-pr` | Filter by whether `tree_prs` array is non-empty. Mutually exclusive. |
| `--unpark-trigger-set` | flag | `--unpark-trigger-set` | Parked threads whose `unpark_trigger` is non-empty — actionable parked threads. Only meaningful with `--status=parked`. |
| `--sort=<key>` | enum | `--sort=modified-desc` | Sort order: `modified-desc` (default, most recent first), `created-desc`, `status` (alpha), `slug` (alpha). |
| `--limit=<N>` | integer | `--limit=20` | Cap number of results. Default: unlimited. |
| `--format=<fmt>` | enum | `--format=json` | Output format: `table` (default, markdown), `json`, `csv`, `yaml`, `paths` (one path per line). |
| `--check-pr-state` | flag | `--check-pr-state` | For in-review threads, invoke `gh pr view` on each `tree_prs[-1]` and enrich output with PR state (OPEN, DRAFT, MERGED, CLOSED). Requires `gh` CLI; gracefully skips if absent with a warning. |
| `--include-archived` | flag | `--include-archived` | By default, `archived` threads are excluded. This flag includes them. |
| `--json-paths-only` | flag | `--json-paths-only` | Emit only file paths to `thread.md` files matching the filters — one per line. Useful for piping to `xargs` or other CLI tools. Equivalent to `--format=paths`. |

**Filter semantics:**
- All filters are AND-ed: a thread must match every supplied filter to appear in results.
- Empty filter set matches all threads in the default status group (`active,parked,in-review`).
- Date filters parse relative (`30d`, `2h`) or ISO-8601 absolute (`2026-04-01T14:30:00Z`). Relative times are computed as "now minus N" in UTC.
- Domain prefix match is case-sensitive. Example: `--domain=eng` does NOT match `engineering/api`.

## Preconditions

The skill **refuses** if any of these are not met.

1. `brain_path` resolves to a directory containing `CONVENTIONS.md`. Defaults to the nearest ancestor `project-brain/` directory; use `--brain=<path>` to override.
2. `project-brain/threads/` exists and is readable.
3. If `--include-archived`, `project-brain/archive/` is readable.
4. If `--check-pr-state`, `gh` is available on the PATH. Absence is a soft fail: the skill continues with a warning and omits the `pr_state` column.
5. All flag values are valid per the table above. Invalid `--status`, `--maturity`, `--sort`, or `--format` values result in immediate refusal with usage hints.
6. Date filter values parse correctly. Malformed relative or ISO-8601 dates result in refusal with a clear error.
7. Numeric `--limit` is a positive integer.

**Path traversal guard:** The skill canonicalizes `brain_path` using `realpath`-equivalent semantics and verifies that all enumerated thread paths are within `brain_path`. Any path escaping is a fatal error (detected but unlikely under normal conditions).

## Process

> ### ⛔️ HARD CONSTRAINT — ONE TOOL CALL
>
> **Call `${CLAUDE_PLUGIN_ROOT}/scripts/discover-threads.sh` ONCE.** No `Read` of thread.md files, no manual frontmatter parsing, no `glob` walks. The script enumerates threads, parses frontmatter, applies filters, sorts, and renders the result.
>
> **Echo the script's stdout in your response message verbatim** — don't summarize, transform, or rely on the Bash tool's result card to display it. The user should see the script's output as part of your reply.
>
> **Derive flags from the user's question, not from defaults.** Examples:
> - "what threads are assigned to alice" → `--assigned=alice`
> - "stale threads in `<some-domain>`" → `--domain=<that-domain> --modified-before=<30-days-ago>`
> - "parked threads needing attention" → `--status=parked --unpark-trigger-set`
> - "what's in review with an open PR" → `--status=in-review --has-pr`

**One call:**

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/discover-threads.sh" \
  --brain=<absolute brain path> \
  [--status=<csv>]              \    # active,parked,in-review,archived (default excludes archived)
  [--owner=<substring>]         \    # case-insensitive substring on owner
  [--assigned=<substring>]      \    # case-insensitive substring on assigned_to list
  [--maturity=<csv>]            \    # exploring,refining,locking
  [--domain=<prefix>]           \    # prefix match on tree_domain
  [--modified-before=<ISO8601>] \
  [--modified-after=<ISO8601>]  \
  [--review-requirement=<value>] \   # exact match
  [--has-pr | --no-pr]          \    # mutually exclusive
  [--unpark-trigger-set]        \    # parked AND unpark_trigger non-empty
  [--include-archived]          \
  [--sort=<key>]                \    # modified-desc | created-desc | status | slug
  [--limit=<N>]                 \
  [--format=<fmt>]                   # table (default) | json | csv | yaml | paths
```

What the script does internally (you don't replicate this):

- Walks `threads/*/thread.md` and optionally `archive/*/thread.md` (when `--include-archived` or `--status=archived` is in play).
- Parses frontmatter via PyYAML (with the pack's stdlib `_yaml_mini` fallback if PyYAML isn't installed). Threads with malformed frontmatter are skipped silently.
- Applies AND-logic filters across all provided flags.
- Sorts (default `modified-desc`) and applies `--limit`.
- Renders in the chosen format. `paths` mode emits newline-separated relative paths suitable for `xargs`.
- Empty result is exit 0 with `(no threads matched)` text in `table` mode, `[]` in `json`, etc.

## Side effects

### Files written or modified

None. The skill is strictly read-only.

| Path (relative to brain root) | Operation | Notes |
|--------------------------------|-----------|-------|
| _(none)_                       | _(none)_  | `thread.md`, `thread-index.md`, `current-state.md` are all byte-identical before and after. |

### Git operations

None. The skill performs no `git add`, `git commit`, `git push`, or any other mutating git invocation. Read-only git operations (e.g., `git status --porcelain` to detect uncommitted edits for warning purposes) are not required by this skill and are not used.

### External calls

- **`gh pr view`** (optional, only when `--check-pr-state` is set) — queries GitHub for the state of each `tree_prs[-1]` URL on in-review threads. Gracefully degrades on absence (warn + omit `pr_state` column) or per-URL fetch error (record `"error"` and continue). Never mutates.

## Outputs

**User-facing summary.** A short message with:

- Count of threads matched and filters applied (e.g. "12 threads matched; 8 shown (limit 10)").
- Warnings (e.g. "2 threads skipped due to malformed frontmatter" or "gh CLI not available; pr_state column omitted").
- Output path or stream indication (e.g. "Results below" for stdout, or "Written to discover-threads-2026-04-22.json").
- Next-step suggestion sized to the context (e.g. "Run `update-thread --assigned=tom` to modify assignment" or "Pass results to `xargs` to operate on matching threads").

**State passed forward.** For programmatic callers:

- `matched_threads` — list of thread records (dicts with all frontmatter fields + optional `pr_state`).
- `matched_count` — total number of threads in results.
- `total_count` — total threads scanned (before filtering).
- `parse_failures` — list of paths that failed to parse.
- `filters_applied` — dict of active filters for audit.

**Output examples:**

Table format (default):
```
| slug | status | maturity | created_by | assigned_to | last_modified_at | tree_domain |
|------|--------|----------|------------|-------------|------------------|-------------|
| hire-backend-lead | active | locking | alice | alice, bob | 2026-04-22T10:00:00Z | engineering/hiring |
| evaluate-crm-vendors | parked | refining | bob | bob | 2026-03-15T14:30:00Z | product/sales |
```

JSON format:
```json
[
  {
    "id": "hire-backend-lead",
    "title": "Hire backend team lead",
    "status": "active",
    "maturity": "locking",
    "created_by": "alice",
    "assigned_to": ["alice", "bob"],
    "last_modified_at": "2026-04-22T10:00:00Z",
    "tree_domain": "engineering/hiring",
    "tree_prs": []
  },
  {
    "id": "evaluate-crm-vendors",
    "status": "parked",
    "maturity": "refining",
    "parked_reason": "Awaiting budget decision",
    "parked_at": "2026-03-15T14:30:00Z",
    ...
  }
]
```

Paths format (one per line):
```
/Users/.../project-brain/threads/hire-backend-lead/thread.md
/Users/.../project-brain/threads/evaluate-crm-vendors/thread.md
```

## Frontmatter flips

None. This is a read-only query skill. No frontmatter fields in any file are modified.

| File | Field | Before | After |
|------|-------|--------|-------|
| _(none)_ | _(none)_ | _(unchanged)_ | _(unchanged)_ |

## Examples

### "What threads are assigned to me?"
```
discover-threads --assigned=tom --format=table
```
Returns all threads (active, parked, in-review) where `assigned_to` contains "tom", in markdown table format.

### "What stale threads in `<some-domain>`?"
```
discover-threads --domain=<some-domain> --modified-before=30d --format=table
```
Returns active/parked/in-review threads under that domain not modified in the last 30 days. Substitute whatever domain you actually have leaves under — the pack ships no domains by default; they emerge organically as you promote.

### "What parked threads are actionable?"
```
discover-threads --status=parked --unpark-trigger-set --format=table
```
Returns parked threads with `unpark_trigger` set — those with a defined resumption condition.

### "What threads require two-human review?"
```
discover-threads --review-requirement=two-human --format=json
```
Returns all matching threads as JSON for downstream processing.

### "Feed a dashboard with live thread state"
```
discover-threads --status=active,in-review --format=json > threads.json
```
Exports the current snapshot of active and in-review threads to a file for CI/dashboard ingestion.

### "What in-review threads have open PRs?"
```
discover-threads --status=in-review --has-pr --check-pr-state --format=table
```
Returns in-review threads with PR URLs, enriched with current PR state (OPEN, DRAFT, MERGED, CLOSED).

### "Export matching thread paths for batch operations"
```
discover-threads --assigned=alice --json-paths-only | xargs -I {} sh -c 'cd {} && update-thread --...'
```
Streams file paths for piping to other tools.

## Postconditions

- No state changes anywhere. `thread-index.md`, `current-state.md`, `thread.md` files are byte-identical before and after.
- No commits, no git operations.
- Output is streamed to stdout or written to a file per the format/redirect.
- If `--check-pr-state` was set and `gh` is absent, a warning appears on stderr; the output continues without the `pr_state` column.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble.
  - Example output: `Found 7 threads matching filter. (table printed.) Done.`
- **normal**: structured summary of what changed (file paths, artifact counts), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Failure modes

| Failure | Cause | Response |
|---------|-------|----------|
| Brain root not found | No `project-brain/CONVENTIONS.md` up the tree; no `--brain` given | refuse — suggest `--brain=<path>` or `cd` to a project dir |
| Invalid `--status` value | Typo; not in `{active, parked, in-review, archived}` | refuse — list valid options |
| Invalid `--maturity` value | Not in `{exploring, refining, locking}` | refuse — list valid options |
| Invalid `--sort` value | Not in `{modified-desc, created-desc, status, slug}` | refuse — list valid options |
| Invalid `--format` value | Not in `{table, json, csv, yaml, paths}` | refuse — list valid options |
| Malformed date filter | Relative format not `\d+[dhms]`; ISO-8601 unparseable | refuse — show example syntax |
| `--limit` not a positive integer | Non-numeric or <= 0 | refuse |
| Frontmatter parse failure on thread | Invalid YAML in `thread.md` | warn — skip the thread; continue with others |
| `gh` not available (with `--check-pr-state`) | PR state check requested but CLI absent | warn — omit `pr_state` column; continue |
| PR fetch error for a specific URL | 404, auth error, network timeout | record state as "error" and continue; do not halt |
| Zero threads match filters | No results | return empty result set; suggest relaxing filters |

Soft failures (malformed frontmatter, PR fetch errors) do not cause the skill to refuse — they are reported as warnings in the summary and the skill continues.

## Related skills

- **Complements:** `verify-tree --rebuild-index` — that skill regenerates the aggregate index on writes; `discover-threads` queries the live source on demand.
- **Invoked before:** `update-thread`, `park-thread`, `discard-thread` — use `discover-threads` to find threads matching criteria, then invoke mutations on the results.
- **Invoked before:** `assign-thread` (future skill) — discovery identifies threads needing assignment changes.
- **Complements:** `materialize-context` — after `discover-threads` finds threads, `materialize-context` can fetch their linked specs.
- **Coordinates with:** any external tool (dashboards, CI, reporting) — the `--format=json` or `--format=paths` output integrates with downstream systems.

## Asset dependencies

None. The skill reads only per-thread frontmatter (and optionally `gh` output). It does not reference any files under the pack's `assets/` directory.

| Asset path | Used at step | Purpose |
|------------|--------------|---------|
| _(none)_   | _(n/a)_      | _(n/a)_ |

## Security / Privacy

- Reads frontmatter only; never exfiltrates thread body content.
- The `--check-pr-state` mode calls `gh pr view` which surfaces PR state and metadata — respects any org-level access restrictions on your `gh` auth.
- Output to stdout or file is the caller's responsibility to protect.
- Date filters are UTC-based; no local-timezone surprises.

## Versioning

**0.1.1** (unreleased — Stage 4 of v0.9.0 cut) — aligned SKILL.md with the 12-section contract in `skill-contract-template.md`: added the three empty-but-required sections (`Side effects`, `Frontmatter flips`, `Asset dependencies`), used `## Inputs` (not `## Inputs / Flags`) as the section heading, and ordered `## Postconditions` before `## Failure modes` per the template's positional order. No behavior change.

**0.1.0** (unreleased — Stage 3 of v0.9.0 cut) — initial release. Discovery/inventory skill that reads per-thread frontmatter directly and returns filtered views on demand. Supports status, assignment, maturity, domain, stale-thread, review-requirement, and PR-state filters. Multiple output formats: table, JSON, CSV, YAML, paths. Works even if aggregate index files are stale.
