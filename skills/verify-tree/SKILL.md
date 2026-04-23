---
name: verify-tree
description: Read-only validator for the project-brain tree. Walks project-brain/ and checks invariants V-01..V-21 covering artifact frontmatter consistency, lifecycle states, soft_links resolution and DAG acyclicity, NODE.md listings, promoted-list uniqueness/monotonicity, debate round sequentiality, source-reference resolution, and ASCII filename safety. Also checks section 11 naming and reserved-filename rules. Reports violations with file and line references, exits non-zero on any error. Can run in standard verify mode (read-only) or in --rebuild-index mode to regenerate thread-index.md and current-state.md from source-of-truth thread frontmatter. Never touches git, never makes network calls. Use when the user says "verify the brain", "validate the tree", "lint the thoughts folder", or as a precondition/postcondition from other skills. Pass --rebuild-index as the final step after any skill that modifies thread state.
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:[brain-root]"
---

# verify-tree

The project brain's lint stage. Every other skill references `verify-tree` in its preconditions or postconditions — the invariants in CONVENTIONS § 9 only matter if something checks them. This skill is that something. It is deliberately small-scoped: it walks the brain, parses frontmatter, and reports violations. Nothing more.

The skill is read-only and side-effect-free. It is safe to run at any cadence — from a pre-commit hook, from CI, from the tail of another skill's process, or by the user on a whim. Because there are no writes, there is no state to corrupt; the worst outcome of a buggy validator is a false positive or a missed violation.

## When to invoke

- "Verify the brain" / "validate the tree" / "lint the thoughts folder"
- As a postcondition check at the tail of `init-project-brain`, `promote-thread-to-tree`, `finalize-promotion`, `derive-impl-spec`, `ai-build`.
- As a staged check during `promote-thread-to-tree` step 4 (`--staging` mode).
- In a pre-commit hook or CI workflow in the brain repo.
- After any manual edit to `project-brain/` the user is uncertain about.

## Inputs

| Name           | Source                         | Required | Description                                                                              |
|----------------|--------------------------------|----------|------------------------------------------------------------------------------------------|
| `brain_path`   | cwd or `--brain=<path>`        | yes      | Root to validate. Defaults to nearest ancestor `project-brain/` directory containing `CONVENTIONS.md`. |
| `scope`        | flags                          | no       | Narrows the walk. Mutually exclusive flags: `--thread=<slug>`, `--path=<relative-path>`, `--staging=<slug>`. Default is full-brain. Ignored when `--rebuild-index` is set. |
| `mode`         | flag                           | no       | `--rebuild-index` switches from validation to index regeneration (see § Rebuild Index Mode). Mutually exclusive with scope flags. |
| `output_mode`  | flag                           | no       | `--format=json` emits machine-readable results; otherwise human-readable. Default human. Only applies to validation mode. |
| `severity`     | flag                           | no       | `--warnings-as-errors` treats § 11 naming-style warnings as errors. Default warnings are reported but do not affect exit code. Only applies to validation mode. |
| `dry_run`      | flag                           | no       | `--dry-run` applies only to `--rebuild-index` mode: runs the full regeneration logic but skips file writes; instead prints diffs to stderr. Useful for CI and debugging drift. |

Flag handling: verify-tree is the one skill in the pack where flags dominate over `AskUserQuestion`. Because it is frequently invoked programmatically by other skills, the interface is designed to be scriptable. When invoked interactively without flags, it defaults to full-brain validation + human output.

## Preconditions

The skill **refuses** if any of these are not met.

1. `brain_path` resolves to a directory containing `CONVENTIONS.md`. If invoked from a subdirectory, the nearest ancestor `project-brain/` wins; if `--brain=<path>` is given, that is authoritative.
2. `CONVENTIONS.md` parses as valid YAML-frontmatter + markdown (content need not match the pack's canonical version — projects customize § 10).
3. For `--staging=<slug>`, `project-brain/threads/<slug>/tree-staging/` exists.
4. For `--thread=<slug>`, `project-brain/threads/<slug>/` exists or `project-brain/archive/<slug>/` exists.
5. For `--path=<relative-path>`, the path is inside `brain_path` (no traversal outside) and exists.

No git state is required. The skill never invokes `git`.

## Process

### Standard validation mode (default)

The skill runs to completion regardless of individual-file errors — the whole point of a linter is to surface every violation in one pass.

1. **Resolve scope.** Determine which files to walk from `brain_path` and scope flags. Full-brain scope covers: `CONVENTIONS.md`, `thread-index.md`, `current-state.md`, `threads/**`, `tree/**`, `archive/**`. `--thread` scopes to one thread; `--staging` scopes to the thread's staging area only; `--path` scopes to an arbitrary subpath.
2. **Walk and parse.** For each `.md` file in scope, parse YAML frontmatter and the body's first `# ` H1. Collect parse errors (missing frontmatter, malformed YAML, missing H1) as V-06 violations.
3. **Classify artifacts.** Tag each file by type from its path and `kind`/`node_type` fields: `thread`, `leaf`, `node`, `impl-spec`, `debate-*`, `index`, `snapshot`, `conventions`. Unclassifiable files in non-exempt paths are V-06 violations (missing required discriminator).
4. **Build cross-reference indexes.** For every artifact, record its `id`, `soft_links`, `tree_prs`, `promoted_to`, `source_thread`, `source_leaf`, `impl_spec`, `source_debate`. This lets invariants V-03, V-11, and the per-state invariants be checked in a single pass.
5. **Check invariants.** Run each invariant in § Invariant registry below against every in-scope artifact. Accumulate violations into a list; do not stop on first error.
6. **Check naming rules.** Per § 11: reserved filename/dir casing (errors), slug format (warnings unless `--warnings-as-errors`), debate round zero-padding and sequencing (errors).
7. **Resolve project-specific extensions.** If `scripts/verify-tree.d/*.py` exists in the brain or pack, each script is imported and its `check(brain, artifacts)` function is invoked. Extensions emit the same violation structure.
8. **Report.** In human mode: print violations grouped by file, each with `file:line: [CODE] message`, sorted by file path then line. End with a summary (`N errors, M warnings`). In `--json` mode: emit `{"errors": [...], "warnings": [...], "summary": {"errors": N, "warnings": M}}` to stdout. Exit 0 if `errors == 0 && (warnings == 0 || !warnings_as_errors)`, else exit 1.

### Rebuild Index Mode (`--rebuild-index`)

When invoked with `--rebuild-index`, the skill regenerates `project-brain/thread-index.md` and `project-brain/current-state.md` from the authoritative thread/leaf frontmatter.

1. **Load source of truth.** Enumerate all `project-brain/threads/*/thread.md` (active + parked) and `project-brain/archive/*/thread.md` (archived) files. Parse each file's YAML frontmatter into an in-memory record: `{ slug, status, maturity, created_at, created_by, last_modified_at, last_modified_by, assigned_to (if set), parked_at/by/reason (if status=parked), archived_at/by (if status=archived), promoted_to, tree_prs, … }`. Also enumerate all leaf files under `project-brain/tree/` for status snapshots.
2. **Validate source files.** Apply frontmatter-required-field invariants (V-01, V-02, V-06, V-08, V-12, V-13) to each thread and leaf. If any file has a parse error or missing required field, REFUSE the rebuild and report the offending artifact — rebuilding from corrupt source would propagate corruption to the indexes.
3. **Compute canonical `thread-index.md`.** Group records by status: Active, Parked, In-Review, Archived. Within each group, sort deterministically:
   - **Active threads:** by `last_modified_at` descending (most recent on top).
   - **Parked threads:** by `parked_at` descending (most recently paused first).
   - **In-Review threads:** by `created_at` descending (newest thread initiatives first).
   - **Archived threads:** by `archived_at` descending (newest archives first).
   For tiebreaks (same timestamp), use slug lexicographically. Render as markdown tables matching the structure defined in `assets/thread-index-template.md` (preserve the template's header, column layout, and any autogenerated-comment blocks).
4. **Compute canonical `current-state.md`.** Summary sections per CONVENTIONS § 4.1 and § 1. Read the existing `assets/current-state-template.md` to match format and placeholders. Include: counts by status, recently-modified active threads (top 5), parked threads with `unpark_trigger` hints, in-review threads with PR URLs, and any cross-cutting notes.
5. **Write atomically.** Write both computed files to temporary paths (`project-brain/.thread-index.md.tmp`, `project-brain/.current-state.md.tmp`). Verify no I/O errors. Then rename (atomic move) the temp files over the live targets. If rename fails, abort without touching the live files.
6. **Verify re-read.** Re-read both written files and confirm the YAML frontmatter and markdown structure parses correctly; this catches silent corruption or truncation.
7. **Exit codes.** Exit 0 on successful rebuild (regardless of whether content changed). Exit 1 on source validation failure (step 2). Exit 2 on write or verify failure (steps 5 or 6).
8. **`--dry-run` compatibility.** If `--dry-run` is also set, skip steps 5–6 (no writes) but run 1–4 and output a unified diff of the computed content vs. the current file content to stderr. Useful for CI checks and debugging drift without modifying the filesystem.

## Side effects

### Files written or modified

None. This skill is read-only.

### Git operations

None.

### External calls

None. Pure-local filesystem read.

## Outputs

**User-facing summary.** In human mode, stderr/stdout gets the grouped violation list and a final count. In `--json` mode, stdout gets a single JSON object and the skill is silent on stderr.

**State passed forward** *(for programmatic callers)*:

- `ok` — boolean; true iff exit code would be 0.
- `errors` — list of `{code, file, line, message, artifact_id}` objects.
- `warnings` — same shape.
- `artifact_count` — total number of artifacts walked.

## Frontmatter flips

None. The skill never writes.

## Invariant registry

Every check has a stable code so callers can programmatically filter or suppress. Codes starting with `V-` track CONVENTIONS § 9 invariants (one-to-one); codes starting with `N-` track § 11 naming rules; codes starting with `X-` are project-specific extensions.

### § 9 invariants

| Code  | Severity | Applies to      | Check                                                                                                  |
|-------|----------|-----------------|--------------------------------------------------------------------------------------------------------|
| V-01  | error    | every artifact  | `title` frontmatter field equals the first H1 of the body (after stripping leading/trailing whitespace). |
| V-02  | error    | leaf, impl-spec | `domain` frontmatter field equals the leaf's actual parent tree path relative to `tree/`.              |
| V-03  | error    | every artifact  | Each `soft_links[].uri` resolves. For `/<tree-path>` the file must exist; for `<alias>:<path>` the alias must be in `projects.yaml` and the resolved path must exist; for `https?://` only syntactic validity (no network fetch). |
| V-04  | error    | node directory  | Every `.md` file in a `tree/<domain>/` directory (except `NODE.md` itself and per-leaf debate/impl-spec sub-files) appears in `NODE.md`'s `## Leaves` section. |
| V-05  | error    | NODE.md         | Every leaf link in `NODE.md`'s `## Leaves` resolves to an existing file.                                |
| V-06  | error    | every artifact  | All required frontmatter fields per § 3.1 + the artifact's type-specific section (§ 3.2–3.5) are present and non-empty (except fields marked nullable). |
| V-07  | error    | thread          | `status` and `maturity` are consistent per § 4.1 table. E.g. `status: in-review` requires `maturity: locking`; `status: archived` requires `maturity` absent. |
| V-08  | error    | thread          | `len(promoted_to) == len(promoted_at)`.                                                                 |
| V-09  | error    | leaf            | Per-state transition invariants from § 4.2 bullets: `in-review` → parent thread has ≥1 entry in `tree_prs`; `decided` → leaf is under `tree/`, not `tree-staging/`; `hardening` → `debate/round-NN/feedback-in.md` exists for the highest N; `specified` → `impl_spec` resolves to file with `status: ready`; `building` → `impl_thread` resolves to an active thread; `built` → `built_in` resolves (URL syntax or SHA); `superseded` → `superseded_by` resolves to a leaf with later `created_at`. |
| V-10  | error    | NODE.md         | `status: decided`. Any other value is a violation.                                                     |
| V-11  | error    | leaf + impl-spec| The pair `(leaf.status, impl-spec.status)` is consistent with § 4.4 table. E.g. leaf `specified` requires impl-spec `ready`; leaf `building` requires impl-spec `building`; etc. |
| V-12  | error    | thread          | Threads with `status: parked` must have all three fields present and non-empty: `parked_at` (ISO-8601), `parked_by` (string), `parked_reason` (string). Threads with `status != parked` must NOT have these fields (absent, not empty-string). |
| V-13  | error    | leaf            | Leaves with `status: hardening` must have a `pre_hardening_status` frontmatter field whose value is one of `{decided, specified}`. Leaves with `status != hardening` must NOT have `pre_hardening_status` set. |
| V-14  | error    | leaf (cond.)    | **Conditional:** fires only when `source_thread` is set. Leaf's `source_thread: <slug>` must resolve to an existing thread. Search in `threads/`, parked-thread locations per CONVENTIONS, and `archive/`. |
| V-15  | error    | any artifact    | The directed graph induced by `soft_links` URIs across all artifacts must be acyclic. Edges point from containing artifact to resolved target (intra-tree only; skip external URIs like `https://`). DFS cycle detection finds any cycle. |
| V-16  | error    | any artifact    | No `soft_links[].uri` may resolve to the containing artifact itself. |
| V-17  | error    | thread          | Within a thread's `promoted_to` array, entries must be unique. Duplicate paths indicate corrupted history. |
| V-18  | error    | thread          | Within a thread's `promoted_at` array, timestamps must be monotonically non-decreasing (later or equal entries come after earlier ones). |
| V-19  | error    | thread + leaf   | Each artifact with a `debate/` subdirectory must have round directories named `round-NN` (zero-padded two-digit) starting from `round-01` with no gaps. If `round-03/` exists, `round-01/` and `round-02/` must both exist. |
| V-20  | error    | leaf (cond.)    | **Conditional:** fires only when `source_debate` is set. Leaf's `source_debate: <path>` must resolve to an existing `debate/round-NN/` directory. |
| V-21  | error    | any artifact    | Artifact filenames and directory names under `project-brain/` must match `^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)?$` (ASCII alphanumeric, hyphen, underscore; at most one dot-separated extension). Exceptions: special fixed names like `NODE.md`, `CONVENTIONS.md`, `README.md`, `thread.md`, `index.md` (exact casing). |

### § 11 naming rules

| Code  | Severity | Applies to              | Check                                                                                   |
|-------|----------|-------------------------|-----------------------------------------------------------------------------------------|
| N-01  | warning  | thread, leaf, NODE.md   | `id` frontmatter matches `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` and is 3–40 chars (§ 11.1).    |
| N-02  | error    | any reserved filename   | Case-exact match for `NODE.md`, `CONVENTIONS.md`, `thread.md`, `decisions-candidates.md`, `open-questions.md`, etc. (§ 11.2). A file named `node.md` or `conventions.md` is an error. |
| N-03  | error    | any reserved directory  | Directories named `thoughts`, `threads`, `archive`, `tree`, `tree-staging`, `debate`, `tryouts`, `diagrams` must be lowercase-exact (§ 11.3). |
| N-04  | error    | debate round directory  | Debate round directories match `^round-\d{2}$`, numbered sequentially starting at `round-01`, no gaps (§ 11.3).                           |

### Invariant details

**V-12: parked-thread required fields.** Threads with `status: parked` must have all three fields present and non-empty: `parked_at` (ISO-8601 timestamp), `parked_by` (string), `parked_reason` (string). Conversely, threads with `status != parked` must NOT have these fields (absent, not empty-string). Detection: iterate over all thread artifacts; for each with `status: parked`, verify all three fields are present and non-empty; for each with `status != parked`, verify none of the three are present. Error templates: `V-12: thread '<slug>' has status=parked but is missing required field(s): <list>.` and `V-12: thread '<slug>' is not parked but has orphan park metadata field(s): <list>.`

**V-13: hardening leaf pre_status.** Leaves with `status: hardening` must have a `pre_hardening_status` frontmatter field whose value is one of `{decided, specified}`. Conversely, leaves with `status != hardening` must NOT have `pre_hardening_status` set. Detection: iterate over all leaf artifacts; for each with `status: hardening`, verify `pre_hardening_status` is present and one of the two valid values; for each with `status != hardening`, verify `pre_hardening_status` is absent. Error templates: `V-13: leaf '<path>' has status=hardening but missing or invalid pre_hardening_status (got: <value>).` and `V-13: leaf '<path>' has pre_hardening_status=<value> but status is <actual> (field is transient and should only exist during hardening).`

**V-14: source_thread resolves (conditional).** This invariant fires only when `source_thread` is set. Leaves with a `source_thread: <slug>` field must have that slug resolve to an existing thread. Search in `project-brain/threads/` (active), any parked-thread location per CONVENTIONS § 3.2 (if the schema designates one), and `project-brain/archive/` (archived). If no match, the leaf has a dangling source reference. Detection: for each leaf with a non-empty `source_thread` field, construct the candidate search paths and check for existence. Cost: O(N) per leaf with source_thread set. Error template: `V-14: leaf '<path>' has source_thread='<slug>' but no matching thread found in active, parked, or archive locations.`

**V-15: soft_links DAG.** The directed graph induced by `soft_links` URIs across all thread and leaf artifacts must be acyclic. Build the graph by treating each artifact as a node and each `soft_links[].uri` that resolves to another artifact in the tree as a directed edge from the containing artifact to the target. Run a DFS cycle detection; any cycle fails the invariant. Skip URIs that resolve outside the tree (e.g. `https://`, `mcp://`) — those are leaf references, not edges in the DAG. Detection: build a resolution table during the cross-reference index phase (step 4 of Process); then run DFS from each unvisited node. Cost: O(V+E) for V artifacts and E resolved intra-tree edges. Error template: `V-15: soft_links form a cycle: <artifact-A> → <artifact-B> → ... → <artifact-A>.` List the full cycle path in the error.

**V-16: soft_links self-reference.** No `soft_links[].uri` may resolve to the containing artifact itself. This catches authoring errors. Detection: for each artifact, resolve every `soft_links[].uri` and check if the resolved path equals the containing artifact's path. Cost: O(1) per soft_link. Error template: `V-16: artifact '<path>' has soft_link '<uri>' that resolves to itself.`

**V-17: promoted_to uniqueness.** Within a thread's `promoted_to` array, entries must be unique. Duplicate paths indicate corrupted history. Detection: for each thread, iterate over `promoted_to` entries and check for duplicates. Cost: O(N) per thread where N is the length of `promoted_to`. Error template: `V-17: thread '<slug>' has duplicate entries in promoted_to: <duplicates>.`

**V-18: promoted_at monotonicity.** Within a thread's `promoted_at` array, timestamps must be monotonically non-decreasing (later or equal entries come after earlier ones). Length parity with `promoted_to` is already enforced by V-08; this adds the ordering constraint. Detection: for each thread, iterate over `promoted_at` entries; verify that each timestamp is >= the previous. Cost: O(N) per thread. Error template: `V-18: thread '<slug>' has non-monotonic promoted_at: entry <i> (<ts_i>) precedes entry <j> (<ts_j>).` List the first pair that violates the ordering.

**V-19: debate round sequentiality.** Each thread or leaf with a `debate/` subdirectory must have round directories named `round-NN` (zero-padded two-digit) starting from `round-01` with no gaps. If `round-03/` exists, `round-01/` and `round-02/` must both exist. Detection: for each artifact with a `debate/` subdirectory, scan the directory contents for `round-*` entries; sort numerically and check for gaps. Cost: O(M log M) per artifact where M is the number of rounds. Error template: `V-19: debate directory '<path>/debate/' has round gap: expected round-<NN>, found jump from round-<prev> to round-<next>.` (List the missing round(s) explicitly.)

**V-20: source_debate resolves (conditional).** This invariant fires only when `source_debate` is set. Leaves with a `source_debate: <path>` field must have that path resolve to an existing `debate/round-NN/` directory. Detection: for each leaf with a non-empty `source_debate` field, verify the path exists and is a directory named matching the pattern `^round-\d{2}$`. Cost: O(1) per leaf with source_debate set. Error template: `V-20: leaf '<path>' has source_debate='<debate-path>' but directory does not exist.`

**V-21: ASCII filename constraint.** Artifact filenames and directory names under `project-brain/` must match `^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)?$` (ASCII alphanumeric, hyphen, underscore; at most one dot-separated extension). Reject emoji, non-ASCII characters, spaces, and other shell-unsafe characters. Exceptions: special fixed names like `NODE.md`, `CONVENTIONS.md`, `README.md`, `thread.md`, `index.md` — keep their exact casing. Detection: during walk (Process step 1), collect all filenames and directory names; for each one not in the exceptions list, test against the regex. Cost: O(1) per filename. Error template: `V-21: path '<path>' contains non-ASCII or unsafe characters. Filenames must match [a-zA-Z0-9_-]+ with optional .ext. See CONVENTIONS § 11.1.`

### Project-specific extensions

Codes prefixed `X-` are defined by scripts in `scripts/verify-tree.d/*.py`. The pack ships no `X-` checks; projects add their own (e.g. an `X-DOMAIN-01` enforcing that every new top-level domain appears in § 10.1 of `CONVENTIONS.md`).

## Postconditions

- The filesystem is unchanged.
- Exit code reflects the pass/fail decision: 0 on no errors (and no warnings-as-errors), 1 otherwise.
- In `--json` mode, stdout is a single JSON object parseable by the caller.
- Every violation includes a file path, line number (or 0 for whole-file issues like missing frontmatter), a stable code, and a human-readable message.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): clean runs (0 errors, 0 warnings) print nothing and exit 0. Violations print in the usual human/json format — the verbosity knob does not suppress signal.
- **normal**: clean runs print a one-line summary: `0 errors, 0 warnings (N artifacts walked).`
- **verbose**: full per-artifact walking trace (pre-rc4 default). Use for debugging.

## Failure modes

| Failure                              | Cause                                                        | Response                                        |
|--------------------------------------|--------------------------------------------------------------|-------------------------------------------------|
| Brain root not found                 | No ancestor `project-brain/` with `CONVENTIONS.md`                | refuse — exit 2 (distinct from validation fail) |
| `CONVENTIONS.md` not parseable       | Malformed YAML or missing frontmatter                        | refuse — exit 2, report parse error              |
| Unknown scope flag combination       | Multiple mutually-exclusive scope flags passed                | refuse — exit 2, print usage                    |
| Extension script import error        | Syntax error in `verify-tree.d/<x>.py`                        | report as a special code `X-IMPORT-ERROR`, continue other checks, exit 1 at end |
| Cycle in `superseded_by` chain       | Two leaves each declare the other as `superseded_by`         | report as `V-09` violation on both leaves       |
| Soft-link URL scheme unrecognized    | `soft_links[].uri` starts with neither `/`, `<alias>:`, `file://`, `https?://`, nor `mcp://` | `V-03` violation with suggestion to use a known scheme |

Validation failures (violations) are reported via exit code 1, never via refusal. Refusals are reserved for invocation errors — the skill cannot answer the question.

## Related skills

- **Invoked as postcondition by:** `init-project-brain`, `promote-thread-to-tree`, `finalize-promotion`, `derive-impl-spec`, `ai-build`.
- **Invoked as pre-landing check by:** `promote-thread-to-tree` step 4 (`--staging`).
- **Compatible with:** every skill in the pack — none write to brain state that would cause verify-tree to fail during their process.
- **Has no precedes/follows relationships:** verify-tree is a leaf in the skill graph; nothing flows forward from it except its exit code and report.

## Asset dependencies

None. The skill reads files from the brain but does not copy from `assets/`. Implementation scripts live in the pack's `scripts/` directory, not `assets/` — they are part of the skill's runtime, not templates.

## Rebuild Index Mode: Determinism and Contract

### Determinism guarantees

The rebuild is fully deterministic. Given the same `project-brain/threads/` and `project-brain/archive/` contents, the regenerated index files are byte-identical regardless of invocation time or environment:

- **Sorting is stable.** Within each status group (Active, Parked, In-Review, Archived), rows are ordered by the primary sort key (timestamp, descending) then by slug (lexicographic ascending) for tiebreaks. The sort is independent of filesystem order or environment variables.
- **Timestamps are ISO-8601 UTC.** All timestamps in frontmatter and computed files are rendered in ISO-8601 format with UTC timezone (e.g. `2026-04-22T14:30:00Z`). No local-timezone conversions, no `date` command invocations.
- **No environment-dependent content.** The regeneration never includes `$USER`, `$(date)`, random seeds, or system-specific values. The output is pure function of the input.

This determinism makes merge conflicts on `thread-index.md` and `current-state.md` trivial to resolve: on conflict, accept either side (or both), then run `verify-tree --rebuild-index` once to produce the canonical version. The conflict becomes a non-event.

### Contract for mutating skills

Every skill that alters thread state **MUST** invoke `verify-tree --rebuild-index` as the final step before exiting successfully. "Altering thread state" includes: creating a thread (`new-thread`), modifying thread fields (`update-thread`), parking/unparking a thread (`park-thread`), promoting/finalizing promotion (`promote-thread-to-tree`, `finalize-promotion`), archiving (`discard-thread`), and any other skill that writes to `thread.md` or leaf frontmatter.

The invocation contract:

- Call `verify-tree --rebuild-index` synchronously at the skill's end (before the success exit).
- If exit code is 0, the index regeneration succeeded; the skill continues and exits 0.
- If exit code is 1 (source validation failure), the skill's own operation has partially succeeded (the thread file was written) but the indexes could not be rebuilt. The skill **must** report this as a failure and either roll back the thread write or report partial success (depending on the skill's commit strategy).
- If exit code is 2 (write/verify failure), the same handling applies: the thread write succeeded but the index write failed; the skill should report and consider rollback.

This contract replaces the previous pattern where each mutating skill separately edited `thread-index.md` and `current-state.md` inline. Those inline edits should be removed by the team owning the mutating skills — `verify-tree --rebuild-index` is now the single source of truth for index regeneration.

### Merge conflicts on index files

Index files are autogenerated; hand-edits will be overwritten on the next `verify-tree --rebuild-index` run. When git reports a merge conflict on `thread-index.md` or `current-state.md`:

1. Resolve the conflict by choosing either side (content will be discarded anyway): `git checkout --ours project-brain/thread-index.md project-brain/current-state.md` or `--theirs`. Both are equivalent.
2. Immediately run `verify-tree --rebuild-index` to regenerate the canonical versions.
3. Commit the regenerated files. The conflict is now resolved deterministically.

This turns a formerly-painful merge conflict into a mechanical operation.

## Versioning

**0.3.0** — Added `--rebuild-index` mode to regenerate `thread-index.md` and `current-state.md` from authoritative thread/leaf frontmatter (the v0.9.0 shift to autogenerated indexes). New flags: `--dry-run` (for use with `--rebuild-index`). Exit codes expanded: 0 = success, 1 = source validation failure, 2 = write/verify failure. Documented determinism guarantees, contract for mutating skills, and merge conflict resolution. Removed inline index edits from skill spec — `verify-tree --rebuild-index` is now the canonical regeneration path. Minor version bump (new mode, new flag, exit code semantics preserved for standard validation mode).

**0.2.0** — Added V-12 through V-21 invariants covering parked threads, hardening leaf transience, source reference resolution, soft_links DAG acyclicity and self-reference, promoted-list uniqueness and monotonicity, debate round sequentiality, and ASCII filename constraints. Major bump for: adding a new V- invariant (breaking — callers relying on "no errors" would start seeing new errors); changing exit code semantics; removing an existing check. Minor bump for: new N- rule, new `--flag`, new output format, project-extension API changes. Patch bump for: wording fixes in error messages, performance improvements.

**0.1.0** — initial draft. Major bump for: adding a new V- invariant (breaking — callers relying on "no errors" would start seeing new errors); changing exit code semantics; removing an existing check. Minor bump for: new N- rule, new `--flag`, new output format, project-extension API changes. Patch bump for: wording fixes in error messages, performance improvements.

## Implementation notes

The SKILL.md is the contract. Implementation details (Python vs Go, frontmatter parser choice, glob library) are in `scripts/verify-tree.py` plus `IMPLEMENTATION.md` sibling to this SKILL.md. Two rules the implementation must honor regardless of language:

1. **Deterministic output.** The same brain state must produce byte-identical reports and index files (excluding timing). Sort violations and index rows deterministically per the specs above. Timestamps always use ISO-8601 UTC. No environment-dependent values.
2. **Bounded memory.** Validator must stream artifacts rather than loading the entire brain into memory. A brain with 10,000 artifacts should validate without blowing past 200 MB resident. Rebuild mode is O(N) in number of threads; per-thread work is O(1) YAML parse + O(L) soft_links traversal. Expect sub-second rebuild on modern hardware at 1000 threads.

Extensions in `scripts/verify-tree.d/*.py` follow the same determinism requirement.

## Performance notes

**Validation cost:** O(N) where N is the number of artifacts in scope. Invariant checks run in one pass; soft_links resolution is O(1) per artifact (hash lookups).

**Rebuild cost:** O(T + L) where T is the number of threads and L is the number of leaves. Per-thread work is O(1) YAML parse + O(soft_links) traversal. At 1000 threads, expect <1 second on modern hardware.

**Rebuild frequency:** Because rebuild runs as the final step of every mutating skill, frequency scales with **write rate**, not read rate — one rebuild per commit, not per query. This is acceptable for most projects (commits per hour, not per second).

## Merge conflict resolution in detail

When working with `--rebuild-index` in a multi-author team, merge conflicts on the index files become expected and harmless. Scenario: Alice pushes a commit that bumps a thread to `in-review`; simultaneously Bob pushes a commit that archives a different thread. Both ran `verify-tree --rebuild-index` before pushing. Git reports a conflict on `thread-index.md`.

**Resolution:**
1. `git checkout --ours project-brain/thread-index.md project-brain/current-state.md` (accept either side; content is temporary).
2. Run `verify-tree --rebuild-index` to recompute the canonical version incorporating both thread changes.
3. Commit the recomputed files.

The result is identical to what would happen if Alice and Bob had merged in sequence: both thread changes appear in the final index, in the correct sort order. No manual merge is needed.

**Why this works:** Because `verify-tree --rebuild-index` is deterministic and reads the thread files (which are already conflict-resolved by git), the regenerated index is unambiguous. It's the closure of both authors' intent.
