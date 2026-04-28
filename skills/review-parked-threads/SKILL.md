---
name: review-parked-threads
description: Read-only periodic audit of parked threads. Surfaces three categories of action-worthy parked threads — actionable (unpark_trigger set; human decides if condition fired), stale (parked ≥N days; candidates for unpark or archive), and hygiene warnings (no unpark_trigger; need explicit reason for return). Use when the user says "review parked threads", "what parked threads need attention", "audit the park queue", or as a weekly/monthly cadence check. Complements discover-threads --status=parked with automatic age and trigger analysis.
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:[brain-root]"
  - Bash (optional; for date computation)
---

# review-parked-threads

Parked threads represent live work paused on external blockers or context shifts. Unlike archived threads (terminal), parked threads are meant to re-enter active work. But without periodic review, parked threads drift: a trigger condition may have fired weeks ago and no one noticed, or the thread lingered long enough that its context is stale.

This skill audits the parked queue on a weekly or monthly cadence, surfacing three categories that warrant human action:

1. **Actionable** — threads whose `unpark_trigger` field suggests the trigger may have fired. E.g., "parked with trigger 'after Q2 kickoff'" and today is past Q2. The skill cannot evaluate natural-language triggers automatically; instead it **surfaces** the trigger text and current date side-by-side, letting the human decide whether to unpark.

2. **Stale** — threads parked longer than the configurable age threshold (default 90 days). These are candidates for either unpark (resume the work) or discard (accept it's never coming back). After 3+ months, re-activation friction is high.

3. **No unpark trigger** — threads parked without an articulated return condition, a hygiene warning. If a thread lacks a trigger, either add one (`update-thread --unpark-trigger=...`) or accept it's aspirational and archive it.

The skill is read-only. It does not park, unpark, or discard anything — it just reports. Output is markdown-report format by default, designed for weekly or monthly review consumption. Optional `--format=json` for machine feeds.

## When to invoke

- "Review parked threads" / "what needs attention in the park queue"
- Weekly / monthly audit cadence (e.g., scheduled at Friday EOD)
- Before archiving a batch: `review-parked-threads --include-stale` to see what's stuck
- "What parked threads are assigned to alice?" — `review-parked-threads --assigned=alice`
- "Export stale parked threads as JSON" — `review-parked-threads --include-stale --format=json`
- After `park-thread` runs, to verify the thread appears in the audit

## Inputs

All flags are optional.

| Flag | Type | Default | Semantics |
|------|------|---------|-----------|
| `--stale-days=N` | integer | 90 | Age threshold in days. Threads parked ≥N days are "stale". |
| `--include-trigger-set` | boolean | true | Include threads with `unpark_trigger` set (the "actionable" category). Set to false to suppress this category. |
| `--include-stale` | boolean | true | Include threads aged ≥ `--stale-days` (the "stale" category). |
| `--include-no-trigger` | boolean | true | Include threads with no `unpark_trigger` (the "hygiene warning" category). |
| `--assigned=<handle>` | string | none | Filter results to parked threads assigned to this owner/collaborator. Case-insensitive substring match against `assigned_to` array. |
| `--domain=<tree-path-prefix>` | string | none | Filter results to parked threads targeting this tree domain (e.g. `--domain=<your-domain>/<sub-area>` matches threads with `tree_domain: <your-domain>/<sub-area>/...`). Case-sensitive prefix match. Substitute whatever folder names exist under your `tree/`. |
| `--format=table\|json\|csv\|markdown-report` | enum | markdown-report | Output format. `markdown-report` (default): human-friendly digest with sections per category. `table`: markdown table (all categories flattened). `json`: JSON array. `csv`: RFC 4180 CSV. |
| `--sort=age-desc\|age-asc\|slug` | enum | age-desc | Sort within each category (or globally if `--format=table`). `age-desc` (default): oldest-parked-first (stalest first). `age-asc`: newest-parked-first. `slug`: alphabetical. |

**Combination semantics:**
- All three category flags (`--include-trigger-set`, `--include-stale`, `--include-no-trigger`) default to true. Setting any to false suppresses that category from the output.
- If all three are set to false, the output is empty (no results). This is a soft pass, not an error.
- `--assigned` and `--domain` filters apply to threads in any category they match.

## Preconditions

The skill **refuses** if any of these are not met.

1. `brain_path` resolves to a directory containing `CONVENTIONS.md`. Defaults to the nearest ancestor `project-brain/` directory; use `--brain=<path>` to override.
2. `project-brain/threads/` exists and is readable.
3. All flag values are valid per the table above. Invalid `--format` or `--sort` values result in refusal with usage hints.
4. `--stale-days` is a non-negative integer.
5. `--assigned` and `--domain` are non-empty strings if supplied.

**Path traversal guard:** The skill canonicalizes `brain_path` and verifies that all enumerated thread paths are within `brain_path`. Any path escaping is a fatal error.

## Process

Each step is read-only and idempotent.

1. **Resolve inputs.** Infer `brain_path` from cwd or `--brain` flag. Parse all filter and format flags. Validate flag values; refuse on error. Compute the effective set of categories to include (based on three `--include-*` flags). Get the current date/time in UTC.

2. **Enumerate parked threads.** Scan `project-brain/threads/*/thread.md` and filter to threads with `status: parked`. Collect file paths and parse frontmatter for each. Extract: `id` (slug), `title`, `status`, `maturity`, `created_at`, `parked_at`, `parked_by`, `parked_reason`, `unpark_trigger` (if present), `assigned_to` (if present), `tree_domain`, `reviewed_at` (optional, for audit trail). On parse failure, emit a warning and skip the thread; accumulate a list of malformed-frontmatter threads to report at the end.

3. **Compute metadata.** For each parked thread:
   - `parked_duration_days` = now() - `parked_at` (rounded down to whole days).
   - `has_unpark_trigger` = boolean, true if `unpark_trigger` field is present and non-empty.
   - `trigger_text` = the `unpark_trigger` string (or null if absent).
   - `is_stale` = `parked_duration_days >= --stale-days`.

4. **Categorize.** Assign each thread to one or more categories (not deduplicated — a thread may appear in multiple categories):
   - **Actionable** — `has_unpark_trigger == true` AND `--include-trigger-set == true`.
   - **Stale** — `is_stale == true` AND `--include-stale == true`.
   - **No-trigger hygiene** — `has_unpark_trigger == false` AND `--include-no-trigger == true`.

5. **Apply filters.** Drop threads that fail any of the optional `--assigned` or `--domain` filters:
   - `--assigned=<handle>`: thread's `assigned_to` array contains a substring match (case-insensitive).
   - `--domain=<prefix>`: thread's `tree_domain` starts with the prefix (case-sensitive).

6. **Sort.** Apply `--sort` order within each category (or globally if `--format` is not `markdown-report`):
   - `age-desc` (default): sort by `parked_duration_days` descending (stalest first). Tiebreak: `slug` ascending.
   - `age-asc`: sort by `parked_duration_days` ascending (newest-parked first). Tiebreak: `slug` ascending.
   - `slug`: sort by slug alphabetically.

7. **Render output.** Format the results per `--format`:
   - **`markdown-report` (default):** A section-per-category digest designed for human review (see § Output formats).
   - **`table`:** Markdown table with all categories flattened. Columns: `slug | category | parked (days) | trigger_text | assigned_to | tree_domain`. (Show trigger text only for actionable category; show staleness only for stale/no-trigger categories.)
   - **`json`:** Array of objects, one per (thread, category) pair. Fields: `slug`, `title`, `category`, `parked_duration_days`, `trigger_text`, `assigned_to`, `tree_domain`, `parked_reason`, `parked_by`, `parked_at`.
   - **`csv`:** Same columns as table format, RFC 4180 CSV-escaped.

8. **Report.** Emit output to stdout. Include a footer with counts (e.g., "3 actionable | 2 stale | 1 no-trigger") and any parse warnings.

## Side effects

### Files written or modified

None. The skill is strictly read-only.

| Path (relative to brain root) | Operation | Notes |
|--------------------------------|-----------|-------|
| _(none)_                       | _(none)_  | `thread.md`, `thread-index.md`, `current-state.md` are all byte-identical before and after. |

### Git operations

None. No `git add`, `git commit`, or `git push` is invoked. This skill never mutates repository state.

### External calls

None required. Date arithmetic is performed in-process (Python/JS built-ins) or via `date -u` if the skill runtime prefers shell; either is an internal implementation detail. No network calls, no MCP tool calls, no `gh` invocations.

## Outputs

**User-facing summary.** A short message with:

- Category counts (e.g., "3 actionable | 2 stale | 1 no-trigger") plus total parked thread count.
- Any warnings (e.g., "1 thread skipped due to malformed frontmatter").
- Output stream indication (stdout by default; file if redirected by the caller).
- A next-step suggestion sized to the result set (e.g., "Run `park-thread --unpark <slug>` on actionable threads whose trigger has fired", or "Run `discard-thread <slug>` on stale threads no longer worth resuming").

**State passed forward.** For programmatic callers:

- `actionable_threads` — list of thread records with `unpark_trigger` set and `--include-trigger-set` enabled.
- `stale_threads` — list of thread records where `parked_duration_days >= --stale-days` and `--include-stale` enabled.
- `no_trigger_threads` — list of thread records with no `unpark_trigger` and `--include-no-trigger` enabled.
- `filters_applied` — dict capturing `--assigned`, `--domain`, `--stale-days`, and category toggles for audit.
- `parse_failures` — list of thread paths that failed to parse (warned, not skipped-silently).

See **§ Output formats** below for the verbatim markdown / table / json / csv shapes.

## Output formats

### markdown-report (default)

```markdown
# Parked-Thread Review — 2026-04-22

## Actionable (trigger set, decide if condition fired)
{N} threads. Human must evaluate whether each trigger text suggests re-activation.

| slug | parked (days) | trigger text | assigned_to |
|------|---------------|--------------|-------------|
| adp-ir-2026-q2 | 18 | after Q2 2026 kickoff | alice |
| evaluate-crm | 32 | when budget approved | bob |

### Stale (parked ≥ 90 days)
{N} threads. Candidates for unpark (resume work) or discard (never coming back).

| slug | parked (days) | assigned_to | tree_domain |
|------|---------------|-------------|-------------|
| old-research | 124 | charlie | product/research |

## No unpark trigger (hygiene warning)
{N} threads. Parked without an articulated return condition. Consider adding trigger or archiving.

| slug | parked (days) | assigned_to | tree_domain |
|------|---------------|-------------|-------------|
| shelved-idea | 45 | dave | <your-domain>/ideas |
```

### table format

All categories in one table:

```markdown
| slug | category | parked (days) | trigger_text | assigned_to | tree_domain |
|------|----------|--------------|--------------|-------------|-------------|
| alpha | actionable | 18 | after Q2 2026 kickoff | alice | <your-domain>/<sub-a> |
| beta | actionable | 32 | when upstream lands | bob | <your-domain>/<sub-b> |
| gamma | stale | 124 | | charlie | <other-domain>/<sub-a> |
| delta | no-trigger | 45 | | dave | <your-domain>/ideas |
```

### json format

```json
[
  {
    "slug": "alpha",
    "title": "Example actionable thread",
    "category": "actionable",
    "parked_duration_days": 18,
    "trigger_text": "after Q2 2026 kickoff",
    "assigned_to": ["alice"],
    "tree_domain": "<your-domain>/<sub-area>",
    "parked_reason": "Q2 planning cycle pending",
    "parked_by": "alice",
    "parked_at": "2026-04-04T14:30:00Z"
  },
  {
    "slug": "gamma",
    "title": "Example stale thread",
    "category": "stale",
    "parked_duration_days": 124,
    "trigger_text": null,
    "assigned_to": ["charlie"],
    "tree_domain": "<other-domain>/<sub-area>",
    "parked_reason": "Waiting for upstream",
    "parked_by": "charlie",
    "parked_at": "2025-11-19T09:00:00Z"
  }
]
```

## Examples

### Weekly review: default behavior
```bash
review-parked-threads
```
Emits a markdown-report digest with all three categories, sorted by age descending (stalest first in each category). Shows actionable triggers, stale-thread candidates, and hygiene warnings.

### Focused: stale threads in a particular domain
```bash
review-parked-threads --domain=<your-domain> --include-stale --include-trigger-set=false --include-no-trigger=false
```
Returns only stale parked threads in the `<your-domain>/*` subtree. Useful for a "cleanup pass" targeting old work in that area. Substitute whatever folder name actually exists under your `tree/` — the pack ships no defaults.

### Machine feed: actionable parked threads as JSON
```bash
review-parked-threads --include-stale=false --include-no-trigger=false --format=json
```
Exports actionable threads (trigger set) as JSON, omitting stale/no-trigger categories. Useful for piping to a dashboard or automation.

### Team assignment check
```bash
review-parked-threads --assigned=alice --format=table
```
Returns all parked threads assigned to alice across all categories, in table format.

### Stale thread audit (CSV export)
```bash
review-parked-threads --stale-days=60 --include-trigger-set=false --include-no-trigger=false --format=csv > stale-parked.csv
```
Exports threads parked 60+ days to CSV for spreadsheet review/archival planning.

## Frontmatter flips

None. This is a read-only audit skill. No frontmatter fields in any file are modified.

| File | Field | Before | After |
|------|-------|--------|-------|
| _(none)_ | _(none)_ | _(unchanged)_ | _(unchanged)_ |

## Postconditions

- No state changes anywhere. `thread.md` files are byte-identical before and after.
- No commits, no git operations.
- Output is streamed to stdout.
- Exactly one pass over the thread directory.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble.
  - Example output: `Reviewed 12 parked threads: 3 actionable, 2 stale, 7 hygiene. Done.`
- **normal**: structured summary of what changed (file paths, artifact counts), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Failure modes

| Failure | Cause | Response |
|---------|-------|----------|
| Brain root not found | No `project-brain/CONVENTIONS.md` up the tree; no `--brain` given | refuse — suggest `--brain=<path>` or cd to project dir |
| Invalid `--format` value | Not in `{markdown-report, table, json, csv}` | refuse — list valid options |
| Invalid `--sort` value | Not in `{age-desc, age-asc, slug}` | refuse — list valid options |
| `--stale-days` not an integer | Non-numeric or negative | refuse |
| Frontmatter parse failure on thread | Invalid YAML in `thread.md` | warn — skip the thread; continue with others |
| All threads filtered out | No results after applying `--assigned`/`--domain` | return empty result; suggest relaxing filters |
| Zero parked threads found | No threads with `status: parked` exist | return message "no parked threads found" to stdout, exit 0 |

Soft failures (malformed frontmatter) do not cause refusal — they are reported as warnings and the skill continues.

## Related skills

- **Complements:** `discover-threads --status=parked` — raw listing without age/trigger analysis. `discover-threads` is a general-purpose query tool; `review-parked-threads` is a domain-specific audit.
- **Invoked before:** `park-thread --unpark` — surface actionable parked threads, then unpark one.
- **Invoked before:** `discard-thread` — surface stale parked threads, then archive ones that are truly dead.
- **Invoked before:** `update-thread --unpark-trigger=...` — surface no-trigger threads, then add missing triggers.
- **Invoked by:** weekly/monthly scheduled review (e.g., via a scheduled task or cron job).

## Asset dependencies

None. The skill reads only per-thread frontmatter from `project-brain/threads/*/thread.md`. It does not reference any templates or files under the pack's `assets/` directory.

| Asset path | Used at step | Purpose |
|------------|--------------|---------|
| _(none)_   | _(n/a)_      | _(n/a)_ |

## Security / Privacy

- Reads frontmatter only; never exfiltrates thread body content.
- Date computation is UTC-based; no local-timezone surprises.
- Output to stdout is the caller's responsibility to protect.

## Versioning

**0.1.1** (unreleased — Stage 4 of v0.9.0 cut) — aligned SKILL.md with the 12-section contract in `skill-contract-template.md`: added the four empty-but-required sections (`Side effects`, `Outputs`, `Frontmatter flips`, `Asset dependencies`), used `## Inputs` (not `## Inputs / Flags`) as the section heading, and ordered `## Postconditions` before `## Failure modes` per the template's positional order. No behavior change.

**0.1.0** (unreleased — Stage 3 of v0.9.0 cut) — initial release. Periodic audit skill that surfaces actionable, stale, and no-trigger parked threads. Supports age threshold configuration, optional filtering by assignment and domain, and multiple output formats (markdown-report, table, JSON, CSV).
