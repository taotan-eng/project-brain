---
id: project-brain-conventions
title: Project Brain Conventions
version: 1.0.0-rc4
status: draft
---

# Project Brain Conventions

This document defines the schema and conventions used by the **project-brain** skill pack. It is the single source of truth for how threads, tree nodes, frontmatter, debates, and cross-references work in any project that installs the pack.

Every skill in the pack reads from this file. If you change the schema, update this file first — the skills and the `verify-tree` validator derive their behavior from what's defined here, not from hard-coded assumptions.

The conventions are designed to be **generic**: a new project should be able to install the pack, run `init-project-brain`, fill in § 10 (project-specific), and get the full ideation → decision → hardening → impl-spec → build → delivery pipeline without writing any project-specific skill code.

### Vocabulary

The pack uses a few terms precisely throughout. When reading the spec or a skill description, assume these meanings:

- **thread** — a thinking container about *one topic*. Lives at `threads/<slug>/`. Private-by-default, exploratory, possibly abandoned. Captured with `new-thread`; refined with `update-thread`.
- **leaf** — *one atomic sub-decision* that came out of a thread, addressable as a single file at `tree/<domain>/<slug>.md`. A thread typically produces multiple related leaves (e.g., an "auth model" thread yields leaves for token type, session store, and logout behavior). Validator-enforced frontmatter contract (`id`, `title`, `status`, `domain`, `source_thread`).
- **NODE.md** — the index file at each `tree/` directory level. Lists leaves in its directory and links to child nodes. Not a leaf itself.
- **decision** — used as general English in prose ("the user decided to use JWT"). When a specific artifact is meant, the text says `thread`, `leaf`, or `NODE.md` instead. The `prior-decision` soft_link role is a specific jargon tag, not the generic word.
- **promotion** — the act of moving selected leaves from `threads/<slug>/tree-staging/` into their final home at `tree/<domain>/`. The `promote-thread-to-tree` skill owns this transition and supports four modes (§ 4.5).
- **artifact** (in the narrow sense) — a file under `threads/<slug>/artifacts/` capturing an intermediate output (debate rationale, benchmark, analysis). `kind: artifact` is a first-class classifier kind with its own frontmatter contract (§ 2.5.2). *Do not confuse with the generic validator use of "artifact" meaning "any markdown file in the brain."*

---

## 1. Directory layout

A project using these conventions has a `project-brain/` folder at its root. This is the **brain root** — every skill in the pack resolves paths relative to this directory. It is deliberately not hidden: the brain is reviewable content, not config.

```
<project>/
  project-brain/                # brain root
    CONVENTIONS.md              # this file (project-customized copy)
    config.yaml                 # optional: per-project config (§ 2, § 2.5)
    thread-index.md             # registry of every thread (active + archived)
    current-state.md            # what's active right now, at a glance
    tree/                       # the shared knowledge tree
      NODE.md                   # root node
      <domain>/                 # domain subdirectories
        NODE.md
        <leaf>.md               # decision leaves
        <leaf>/                 # or a leaf-as-directory when it has companions
          <leaf>.md
          debate/               # optional: multi-agent hardening artifacts
          impl-spec.md          # optional: implementation spec
    threads/
      <slug>/                   # one directory per thread
        thread.md               # frontmatter + freeform notes
        transcript.md           # optional: append-only human-LLM log (§ 2.5)
        artifacts/              # optional: structured markdown products with frontmatter (§ 2.5.2)
        attachments/            # optional: raw/binary evidence (PDFs, CSVs, screenshots) — no frontmatter contract
        decisions-candidates.md
        open-questions.md
        proposal.md             # optional
        diagrams/               # optional
        tree-staging/           # promotion staging area (pre-PR)
    archive/                    # completed / retired threads
```

The `project-brain/` folder is tracked in git and reviewable via PR. Nothing below `project-brain/` should be machine-generated without also being checked in — the tree is authoritative, not derived.

Exceptions inside a thread directory, graded by how much structure the validator enforces:

- `transcript.md` is an append-only human-LLM conversation log. No frontmatter contract (`kind=transcript` is in `KINDS_WITHOUT_FRONTMATTER`). Gitignored by default; commit it if you want the conversation in PR history.
- `attachments/` holds raw/binary evidence (PDFs, CSVs, screenshots, scratch scripts) — no frontmatter, no file-structure rules. Gitignored by default.
- `artifacts/` holds structured markdown products written by `record-artifact` (§ 2.5.2) — debate rationales, analyses, benchmarks. Each is a `.md` file with required frontmatter (`id`, `title`, `kind: artifact`, `created_at`, `source_thread`). V-01/V-06 apply, plus V-22 (source_thread must match the parent thread dir). These ARE committed with the thread — they're product evidence, not scratch work.

### 1.1 Host-environment binding (1:1, new in v1.0.0-rc4)

One project-brain corresponds to **exactly one** host-environment project. The "host" is whatever agent runtime the user is operating in:

| Host runtime      | What counts as "the project" |
|-------------------|------------------------------|
| Cowork (Claude Desktop) | The user-selected workspace folder |
| Codex             | The bound project directory |
| Claude Code CLI   | The cwd at session start    |
| Other / scripts   | The cwd, or an explicit `--brain=<path>` |

The brain lives at `<host-project-root>/project-brain/`. Switching projects is a **host-level operation** — open a different Cowork session, start Codex in a different directory, `cd` before invoking Claude Code. Project-brain does not maintain a separate "active project" state; there is no `switch-project` skill and no session-scoped pointer. When the host's binding changes, the brain resolution follows automatically on the next skill invocation.

Consequences of the 1:1 contract:

- `init-project-brain` detects the host project root via `scripts/verify_tree/config.py::detect_host_project_root()` (env-var probes + `.git/` walk, zero shell invocations) and scaffolds `project-brain/` inside it. The default flow asks zero interactive questions in the common case.
- `find_brain_root()` in the validator walks cwd upward for `CONVENTIONS.md`. In the 1:1 world this is equivalent to "find the nearest ancestor that is a project-brain project."
- The user-global registry at `~/.config/project-brain/projects.yaml` (§ 2.2) has a narrow, purely cross-project role — it lets `soft_links` URIs of the form `<alias>:<path>` resolve across distinct host projects. It is **not** a session-context mechanism. A user who never emits cross-project `soft_links` never needs to create it.
- Monorepo case: if a host project directory contains multiple sibling brains (e.g., `monorepo/frontend/project-brain/` and `monorepo/backend/project-brain/`), skills resolve the nearest brain via cwd-walk. Ambiguity is surfaced honestly — there is no implicit "top-level brain" election. Users `cd` into the sub-project to operate on its brain.

### 1.2 Source of truth: per-thread frontmatter

Of the files above, **`thread-index.md` and `current-state.md` are autogenerated projections**, not authored artifacts. The single source of truth for any thread's state is that thread's own `thread.md` frontmatter (§ 3.2). The aggregate files exist so a human can open `project-brain/thread-index.md` or `project-brain/current-state.md` and see the fleet at a glance, but their content is deterministically rebuilt by `verify-tree --rebuild-index` from the per-thread frontmatter.

Consequences that follow from this model:

- Mutating skills (every skill that creates, modifies, parks, unparks, archives, promotes, or finalizes a thread) invoke `verify-tree --rebuild-index` as their final step and stage the regenerated index files in the same commit as their per-thread changes.
- Hand-edits to `thread-index.md` or `current-state.md` are not an error, but they will be silently overwritten on the next rebuild. Both files carry an explicit `AUTO-GENERATED` header to make this clear.
- Merge conflicts on these two files are trivial to resolve: accept either side (`git checkout --theirs`/`--ours`), then run `verify-tree --rebuild-index`. The result is identical regardless of which side was accepted because the rebuild is deterministic over the per-thread frontmatter.
- `NODE.md`, `thread.md`, leaf files, `decisions-candidates.md`, `open-questions.md`, and every file under `tree/` are NOT autogenerated — they are authored content.

---

## 2. Project alias registry

Alias resolution uses a **two-layer model** (new in v1.0.0-rc4):

1. **Per-project** — `<brain>/config.yaml`. Authoritative for this brain. Required for cross-project `soft_links` that this brain emits; otherwise optional.
2. **User-global** (opt-in) — `$XDG_CONFIG_HOME/project-brain/projects.yaml`, falling back to `~/.config/project-brain/projects.yaml`. Optional. Useful only if you want the *same* alias to resolve from multiple brains without duplicating the entry.

Alias lookup precedence: per-project → global → unresolvable (V-03 warning, not error).

A brain that never references another project has no need for either file. **The pack is fully functional without any `~/` access.** Refusing to create a home-dir config never breaks a brain; it only prevents the global registry from being consulted.

### 2.1 Per-project config (`<brain>/config.yaml`)

Describes *this* brain and the aliases *this* brain uses.

```yaml
# <brain>/config.yaml
primary_project: my-app        # alias of this brain — must match thread frontmatter

# Cross-project references this brain resolves itself. Optional.
aliases:
  adp:
    brain: /home/you/workspace/adp/project-brain
    # Optional: remotes used when this brain emits a cross-project PR.
    remotes:
      - name: origin
        url: git@github.com:your-org/adp.git
        default_base: main
    default_remote: origin

# Operational knobs (§ 2.5). Optional.
verbosity: terse               # terse | normal | verbose      (default: terse)
transcript_logging: on         # on | off                      (default: on)
```

### 2.2 User-global registry (`~/.config/project-brain/projects.yaml`)

Optional. Flat top-level mapping of alias → descriptor. Consulted only when an alias is not listed in the per-project `aliases:` block.

```yaml
# ~/.config/project-brain/projects.yaml
adp:
  root: ~/workspace/adp
  brain: ~/workspace/adp/project-brain
  remotes:
    - name: origin
      url: git@github.com:your-org/adp.git
      default_base: main
  default_remote: origin

# Multi-remote example: a fork-based workflow where promote PRs go to upstream
# from a personal fork.
myapp:
  root: ~/workspace/myapp
  brain: ~/workspace/myapp/project-brain
  remotes:
    - name: origin                     # your fork
      url: git@github.com:you/myapp.git
      default_base: main
    - name: upstream                   # canonical repo; PRs land here
      url: git@github.com:org/myapp.git
      default_base: main
  default_remote: upstream
```

### 2.3 Shared schema notes

- `remotes` is a list even when there's only one entry. The common case (single remote) still requires the list form — this keeps the schema uniform for validators and avoids per-project branching logic in skills.
- `default_remote` is required when `remotes` has more than one entry; for single-remote projects it may be omitted (defaults to the only entry).
- `default_base` is per-remote. At promote time the skill uses it as the *default* base branch, but **always prompts** — threads within one project routinely land on different branches (feature branches, release trains, etc.).
- `url` is informational for the registry. The actual push target is looked up via `git remote get-url <name>` inside the brain repo.
- Environment overrides honoured by the validator: `PROJECT_BRAIN_CONFIG` (per-project config path), `PROJECT_BRAIN_PROJECTS_YAML` (global registry path). Both are primarily for tests and CI.

Skills resolve project-aliased URIs (e.g. `<alias>:<some-domain>/<some-path>.md`) through the two-layer model. This decouples addressing from filesystem location — repos can move without breaking refs.

### 2.4 V-03 severity rules for alias refs

- **No layer present** (neither per-project `config.yaml` nor a global registry) → V-03 *warning* (not error). The soft_link is unverified but the brain remains usable. Authors who never emit cross-project refs never see this warning.
- **Some layer present, alias not listed** → V-03 *error*. The author declared they use an alias registry but forgot to list this alias.
- **Alias listed but target doesn't exist on disk** → V-03 *error*.

---

## 2.5 Operational config — verbosity and transcript logging

The per-project `config.yaml` carries two runtime knobs that adjust skill behavior:

### verbosity: `terse | normal | verbose`

Controls how much prose a skill emits alongside its file operations. Default is `terse`.

- **terse** (default): one acknowledgement line naming what's being written and where, then `Done.` No command narration, no tool-output echo, no "let me..." preamble.
- **normal**: structured output of write operations without conversational framing.
- **verbose**: full narration (pre-rc4 default). Useful for debugging.

Environment override: `PROJECT_BRAIN_VERBOSITY=<level>`.

### transcript_logging: `on | off`

Controls whether mutating skills write verbatim human-LLM transcripts into `<thread>/transcript.md`. Default is `on`.

- **on**: each session appends structured entries (see § 2.5.1) to `<thread>/transcript.md`. `thread.md` remains the curated summary; `transcript.md` is the verbatim log.
- **off**: no transcript written. `thread.md` stays the only narrative.

Per-thread override lives in thread frontmatter as `transcript: off` for threads where verbatim logging isn't wanted (sensitive content, etc.).

Environment override: `PROJECT_BRAIN_TRANSCRIPT=on|off`.

### 2.5.1 transcript.md entry format

`transcript.md` is append-only and human-readable (the product decision for rc4; machine re-ingestion is future work). Every skill that writes transcripts MUST follow the schema below so downstream tooling can parse transcripts back into context without bespoke per-skill parsers.

**File structure.** No YAML frontmatter (the file is in `KINDS_WITHOUT_FRONTMATTER`, § 9). One `# transcript` H1 at the top of a fresh file; every subsequent session appends entries without rewriting anything above them.

**Entry structure.** Each entry is a level-2 heading block:

```markdown
## <ISO-8601 timestamp> — <role> [— <skill>]
<free-form content>

[optional: Tool calls:
- <verb> <target>
- <verb> <target>
]

[optional: Attachments:
- <relative path under <thread>/attachments/>
]
```

**Field conventions:**

- `<ISO-8601 timestamp>` — UTC, second precision, trailing `Z` (example: `2026-04-23T14:12:04Z`). Timestamps monotonically non-decreasing within a file.
- `<role>` — one of `user`, `assistant`, `tool`. Skills write their own output as `assistant`.
- `<skill>` (optional) — the invoking skill name on `assistant` entries, so transcripts can be filtered by skill: `— assistant — new-thread`.
- Content is verbatim freeform markdown. No token-count trimming; don't paraphrase.
- `Tool calls:` and `Attachments:` sub-sections are optional; present only when relevant. Each entry in those sub-sections is a single line under a bullet.
- Code blocks, tables, and other markdown inside `<free-form content>` are allowed. Backtick-fenced code is preserved as-is.

**Example — a `new-thread` session appending two entries:**

```markdown
# transcript

## 2026-04-23T14:12:00Z — user
Start a new thread. I've been thinking through `<some-decision>`.

## 2026-04-23T14:12:04Z — assistant — new-thread
Captured. Thread slug `<example-slug>`, owner `alice@example.com`.

Tool calls:
- Write project-brain/threads/<example-slug>/thread.md
- Write project-brain/threads/<example-slug>/decisions-candidates.md
- Write project-brain/threads/<example-slug>/open-questions.md
- Exec verify-tree --rebuild-index

Attachments:
- napkin-sketch.png
```

**Why this shape:** level-2 headings are trivial to parse with a regex or a simple line walker; timestamps are sortable as strings; `## ` is visually distinct from in-content headings (which should go to `###` or deeper). Free-form content between headings means skills don't have to escape prose through a structured format like JSONL while still letting future tooling chunk the file into per-entry records.

**Skills MUST NOT:**
- Rewrite entries written in earlier sessions.
- Insert entries anywhere other than the end of the file.
- Summarize or paraphrase user input — content is verbatim.
- Write transcripts when `transcript_logging: off` or the thread's frontmatter has `transcript: off`.

### 2.5.2 Artifacts — structured thread products

`record-artifact` captures intermediate outputs — debate rationales, analyses, benchmarks, sketches, reference files — into a thread without requiring the user to decide layout. The skill routes inputs by file kind:

- **Markdown inputs** (the common case: debate writeups, analyses, rationales) land in `<thread>/artifacts/NNNN-<title-slug>.md`. Frontmatter is injected from `assets/artifact-template.md`. `kind: artifact` is a first-class classifier kind; V-01 (title/H1 parity), V-06 (required fields: `id`, `title`, `kind`, `created_at`, `source_thread`), and the new V-22 (artifact `source_thread` matches parent thread dir on disk) all apply. `artifact_kind` is a free-form label in frontmatter (common values: `debate`, `analysis`, `benchmark`, `sketch`, `reference`, `other`) used for grouping in `review-thread` output.
- **Non-markdown inputs** (PDFs, CSVs, PNGs, raw logs) land in `<thread>/attachments/` unchanged. No frontmatter contract — `kind: attachment` is in `KINDS_WITHOUT_FRONTMATTER`. Filenames that look like tempfiles are renamed using the artifact title slug so listings stay readable.

Artifacts and attachments live side-by-side under the thread. The distinction is structural, not semantic: anything a human would want to annotate, diff, or reference by path belongs in `artifacts/`; raw opaque blobs belong in `attachments/`.

**Transcript breadcrumb.** Every `record-artifact` invocation — default mode or `--append` — writes an entry to `transcript.md`. Default mode writes a breadcrumb pointing at the created file(s); `--append` mode writes the content itself into the transcript under an H2 block. This means the transcript always reflects the full chronological flow, even when the products are separate files.

**Numbering.** `NNNN-` sequential prefix. The script scans `artifacts/[0-9][0-9][0-9][0-9]-*.md` to find the next free number. Sequential beats timestamped for UX (easier to say "see artifact 3") and collisions within the same millisecond are rare in human-speed workflows.

**Promotion.** Artifacts stay under the thread after `promote-thread-to-tree` by default — they're thread-scoped history. Leaves can soft_link back to specific artifacts using `threads/<slug>/artifacts/NNNN-<slug>.md`. Future: `promote-thread-to-tree --promote-artifact=<path>` will optionally carry selected artifacts into `tree/<domain>/<leaf>/artifacts/`.

### .gitignore defaults

`init-project-brain` writes a `.gitignore` next to the brain with the following entries by default:

```
# project-brain v1.0.0-rc4 defaults
project-brain/threads/*/transcript.md
project-brain/threads/*/attachments/
project-brain/archive/*/transcript.md
project-brain/archive/*/attachments/
```

Rationale: transcripts and attachments are reproducible evidence, not curated artifacts. The durable record is `thread.md` plus `artifacts/` (which ARE committed — they're structured products, not scratch work). Users who want PR-reviewable transcripts delete the relevant lines.

---

## 3. Frontmatter schema

All `thread.md` files, tree leaves, and NODE.md files carry YAML frontmatter.

### 3.1 Shared fields (all artifacts)

```yaml
id: <slug>                     # URL-safe; stable for the life of the artifact
title: <string>                # human-readable; must match the H1 heading
created_at: <ISO-8601>
owner: <string>                # email or github handle
primary_project: <alias>       # key from projects.yaml
related_projects: []           # other aliases this touches; empty by default
soft_links:                    # URI-typed refs; see § 5
  - uri: <uri>
    role: <role>               # optional; see § 5.2
status: <lifecycle-state>      # see § 4
```

### 3.2 Thread-only fields

```yaml
maturity: exploring | refining | locking
tree_domain: <path>            # guess at where this promotes; nullable while exploring
tree_node_type: leaf | node    # set once the promotion shape is known
tree_prs: []                   # promotion PR URLs; grows per cycle (most recent last)
promoted_to: []                # per-leaf tree paths, appended at each merge
promoted_at: []                # ISO-8601 timestamps, one per entry in promoted_to
impl_thread: <slug>            # if an implementation thread forks from this
built_in: <pr-url-or-commit>   # set when the implementation lands
archived_at: <ISO-8601>        # set by finalize-promotion or discard-thread; absent on active threads
archived_by: <string>          # email or handle recorded alongside archived_at
discard_reason: <string>       # set by discard-thread when a thread is killed pre-promotion; absent otherwise
parked_at: <ISO-8601>          # set by park-thread; absent on non-parked threads
parked_by: <string>            # email or handle recorded alongside parked_at
parked_reason: <string>        # short "why paused"; required when parked
unpark_trigger: <string>       # optional; describes what would cause re-activation (e.g. "after Q3 planning")
last_debate_round: <path>      # optional; relative path to the most recent debate/round-NN/ if multi-agent-debate was run against the thread. Persists across round close for audit.
assigned_to: []                # optional; free-form list of owner/collaborator handles (GitHub, Slack, email, whatever the project prefers). Semantics intentionally open per project policy: single-owner, multi-collaborator, or role-based are all valid. Pack skills read and surface this field (e.g. discover-threads filters by it) but do NOT enforce any model — teams wire enforcement via CODEOWNERS, branch protection, or their own tooling.
review_requirement: <string>   # optional; free-form string describing the review policy for this thread's eventual promotion. Example vocabulary: "one-human", "two-human", "codeowners", "optional", "legal-sign-off". Pack skills surface this field but do NOT enforce it — the pack stays policy-neutral so it works across teams with different review cultures.
```

Both `assigned_to` and `review_requirement` are unenforced by the pack. They exist as structured fields so skills, tooling, and humans can converge on a shared vocabulary without the pack dictating policy. Teams that want enforcement should wire it externally (CODEOWNERS, branch protection rules, CI checks, bot automation) rather than expecting skills to refuse on the basis of these fields.

### 3.3 Leaf-only fields

```yaml
node_type: leaf | node
domain: <tree-path>            # this leaf's location
source_thread: <slug>          # the thread this was promoted from
source_debate: <path>          # optional: debate round dir if hardened
impl_spec: <path>              # relative to the leaf; set when derive-impl-spec runs
built_in: <pr-url-or-commit>   # set on code merge
superseded_by: <tree-path>     # optional
pre_hardening_status: <decided|specified>  # transient; written by multi-agent-debate on round open, removed on round close. Present iff status == hardening.
```

### 3.4 NODE.md fields

Same as leaf fields, plus:

```yaml
node_type: node
children: []                   # sub-domains (derived; kept for validator sanity)
```

### 3.5 Impl-spec fields

Lives at `<leaf-dir>/impl-spec.md`. Uses shared fields (§ 3.1) plus:

```yaml
kind: impl-spec                # discriminator so skills don't rely on filename alone
source_leaf: <tree-path>       # the leaf this impl-spec builds from
source_debate: <path>          # optional; omit if not hardened
```

`status` values follow the impl-spec lifecycle (§ 4.4): `draft | ready | building | built | stale`.

---

## 4. Lifecycle states

Frontmatter flips are **skill-driven**, not manual. No skill is allowed to leave an artifact in an inconsistent state — a flip is part of the same commit as the substantive change. Every row below names the triggering skill so `verify-tree` and downstream tooling can audit ownership.

Threads cycle: a thread with multiple waves of promotion re-enters `active` after each merge or PR close. Leaves advance primarily along a linear chain, with `hardening` as a transient state that can enter from either `decided` or `specified` and exits back to the state it came from.

### 4.1 Thread lifecycle

Primary states: `active | parked | in-review | archived`. `maturity` progresses independently inside `active`. `parked` is a pause state with no maturity progression — the maturity value from before the park is preserved in frontmatter so `park-thread --unpark` can restore it.

| status      | maturity    | flipped by                    | meaning                                              |
|-------------|-------------|-------------------------------|------------------------------------------------------|
| `active`    | `exploring` | `new-thread`                  | Freshly scaffolded; free-form thinking.              |
| `active`    | `refining`  | `update-thread` or author     | Candidates identified; narrowing scope.              |
| `active`    | `locking`   | `update-thread` or `promote-thread-to-tree` | Staging underway; PR not yet open.     |
| `parked`    | *(preserved)* | `park-thread`                | Alive but paused; reason captured in `parked_reason`. Maturity from prior state preserved so unpark can restore it. |
| `active`    | *(restored)* | `park-thread --unpark`        | Un-parked; returns to the maturity held before the park. |
| `in-review` | `locking`   | `promote-thread-to-tree`      | Promotion PR URL received; frontmatter synced.       |
| `active`    | `refining`  | `finalize-promotion`          | Re-entry after PR merges; more work left. (On PR close-without-merge, `discard-promotion` restores `active` without archiving.) |
| `archived`  | —           | `finalize-promotion` (choice) or `discard-thread` (pre-promotion kill) | Thread complete; moved to `project-brain/archive/`.  |

Notes on cycling:

- `tree_prs` grows by one URL each time a promotion PR opens (most recent last).
- On merge, `promoted_to` and `promoted_at` each gain one entry per merged leaf.
- On PR close without merge, no entries are added; `tree_prs` retains the closed URL for audit.
- Transition to `archived` is always explicit and requires `maturity != locking`.
- Transitions into `parked` are allowed only from `active` (any maturity). A thread in `in-review` cannot be parked — close or merge the PR first.
- `discard-thread` is the only path from `active` or `parked` to `archived` when `tree_prs` is empty (no PR history). If `tree_prs` is populated and the final PR is still OPEN, close it on the host first; if CLOSED-unmerged, use `discard-promotion`; if MERGED, use `finalize-promotion` with the archive disposition.
- **`restore-thread`** is the inverse of `discard-thread`: it brings an `archived` thread back to `active`. The original `discard_reason` and `archived_*` fields are stripped from frontmatter on restore but preserved as a one-line audit comment in the thread body so the round-trip is visible.
- **`in-review` is read-only**: `update-thread`, `park-thread`, and `discard-thread` all refuse on `in-review` threads. To edit an `in-review` thread, the canonical escape hatch is **`discard-promotion`** — it accepts both CLOSED-unmerged PRs (the original case) AND OPEN PRs (user-initiated mid-review cancel; the skill closes the PR itself via `gh pr close`). Either way the thread reverts to `active/refining`, the PR URL stays in `tree_prs` for audit, and the user can edit and re-promote when ready. This is preferred over selectively loosening `update-thread`'s gate because it gives users one rule (`in-review = read-only; revert via discard-promotion`) rather than an operation-by-operation matrix. Reviewer comments on a canceled OPEN PR persist on the (now-closed) PR for later reference.
- **Local-mode promotion** (`--mode=local`, see § 4.5) skips `in-review` entirely: leaves move from `tree-staging/` to `tree/` directly, and the thread stays `active` throughout. The escape-hatch question above only applies to git-mode promotions.
- **Thread-scope debate** (`multi-agent-debate --scope=thread`) may run any number of times during `active` refinement. It creates `threads/<slug>/debate/round-NN/` rounds and updates `last_debate_round`, but **does not flip `status` or `maturity`** — the thread stays wherever it was. Leaves are the only artifact kind whose status transitions through `hardening`. A thread in `parked` or `in-review` cannot accept a new debate round.

### 4.2 Leaf lifecycle

Primary chain: `draft → in-review → decided → specified → building → built`. `superseded` is an orthogonal terminal state reachable from any post-`draft` state. `hardening` is a transient state enterable from `decided` or `specified`, exits back to whichever it came from.

| status        | flipped by                       | meaning                                                   |
|---------------|----------------------------------|-----------------------------------------------------------|
| `draft`       | `promote-thread-to-tree`         | Exists in `tree-staging/` or on a PR branch pre-URL.      |
| `in-review`   | `promote-thread-to-tree`         | PR URL pasted back; frontmatter synced to PR state.       |
| `decided`     | `finalize-promotion`             | Promote PR merged; leaf flipped from `in-review` on main. |
| `hardening`   | `multi-agent-debate`             | A debate round is open under `debate/round-NN/`.          |
| `specified`   | `derive-impl-spec`               | Impl-spec exists and is `ready` (see § 4.4).              |
| `building`    | `ai-build`                       | Implementation thread active; code PR not yet merged.     |
| `built`       | `ai-build`                       | Code PR merged; `built_in` populated.                     |
| `superseded`  | author explicit                  | `superseded_by` populated; read-only historical record.   |

Transition invariants (enforced by `verify-tree`):

- `in-review` requires at least one entry in the parent thread's `tree_prs`.
- `decided` requires the file to exist at its `domain` path (not in `tree-staging/`).
- `hardening` requires `debate/round-NN/feedback-in.md` to exist for the highest N.
- `specified` requires `impl_spec` frontmatter field to resolve to a file with `status: ready`.
- `building` requires `impl_thread` frontmatter field to resolve to an active thread.
- `built` requires `built_in` to be a resolvable PR URL or commit SHA.
- `superseded` requires `superseded_by` to resolve to a leaf whose `created_at` is later.

### 4.3 NODE.md lifecycle

NODE.md is created `decided` by `promote-thread-to-tree` (for a new sub-tree) or by `init-project-brain` (for the root) and stays in `decided`. It does not harden, specify, or build. A NODE.md with any other status is a validator error.

### 4.4 Impl-spec lifecycle (internal to the artifact)

An impl-spec lives at `<leaf-dir>/impl-spec.md` and carries its own `status` field independent of the leaf it sits under. The two lifecycles are coupled only at specific transitions:

| impl-spec status | flipped by          | effect on parent leaf                        |
|------------------|---------------------|----------------------------------------------|
| `draft`          | `derive-impl-spec`  | Leaf stays `decided`; impl-spec being drafted.|
| `ready`          | author explicit     | Leaf flips `decided → specified`.            |
| `building`       | `ai-build`          | Leaf flips `specified → building`.           |
| `built`          | `ai-build`          | Leaf flips `building → built`.               |
| `stale`          | `multi-agent-debate` patches landed | Leaf flips back to `decided` until re-derived. |

A leaf's status is always a function of its impl-spec's status at transitions marked above; at all other times the two move independently.

### 4.5 Promotion modes

`promote-thread-to-tree` supports four modes, chosen to match the user's git/review setup. The mode affects *how* leaves move from `threads/<slug>/tree-staging/` into `tree/<domain>/`, but not *what* ends up in the tree — the resulting `tree/` state is identical in every mode.

| Mode          | Stages files | Creates branch | Commits | Pushes | Creates PR | Use when                                                 |
|---------------|--------------|----------------|---------|--------|------------|----------------------------------------------------------|
| `local`       | ✓            | —              | local, optional | — | —        | Solo users, offline, no GitHub. Review happens in your head. |
| `git:pr`      | ✓            | ✓              | ✓       | ✓      | ✓ (`gh`)   | Power users with git + gh set up. Full automation.       |
| `git:branch`  | ✓            | ✓              | ✓       | ✓      | —          | Team reviews outside GitHub (GitLab, self-hosted, Slack). |
| `git:manual`  | ✓            | ✓              | —       | —      | —          | User wants full manual control over commits/pushes.      |

**Mode resolution chain** (implemented by `promote-thread-to-tree`):

1. If `--mode=<value>` is passed explicitly → use it.
2. Else read `<brain>/config.yaml` for `promote_mode_default`. If set to one of the four values → use it.
3. Else probe git + gh readiness silently (no mutations): `git rev-parse --is-inside-work-tree`, `git config user.email`, `git remote get-url origin`, `gh auth status`. All four pass → auto-default to `git:pr` and note the source in the output.
4. Any probe fails → present one `AskUserQuestion` with three options:
   - **Stay local** (default) — proceed with `--mode=local`.
   - **Set up git** — print the exact commands the user should run (`git config --global user.email ...`, `gh auth login`, etc.), exit without promoting. User re-invokes after setup.
   - **Cancel** — exit cleanly, no files touched.
5. `--remember-mode` on any invocation persists the chosen mode into `config.yaml`'s `promote_mode_default` key, so subsequent promotions skip the question.

**Why four modes, not two.** A naive "git vs no-git" split glosses over two common cases: teams using non-GitHub review (where `gh pr create` doesn't fit but git itself does), and power users who want Claude to do the file work but not touch `git commit`. The four-mode taxonomy lets each user pick the automation boundary they prefer; the resolution chain makes the default intelligent without forcing a prompt on someone who already has gh authed.

**Local mode does not break the philosophy.** The pack's invariant is "markdown-first; git is a collaboration tool layered on top, not a prerequisite for thinking." A solo user without a GitHub account should be able to capture, refine, debate, and lock a decision without ever touching `git remote add`. `--mode=local` delivers that: `tree/` gets the same validator-clean leaves, `NODE.md` indexes stay consistent, and the `promoted_to`/`promoted_at` audit fields record where each leaf landed. If the user later connects a remote, the historical decisions are already present and pushable in one commit.

---

## 5. `soft_links`: URI-typed refs

`soft_links` accept any URI scheme. Each entry is an object with `uri` (required) and optional `role`. This is the single cross-reference field across the entire pack — there is no parallel `context_refs` or `references` field.

### 5.1 Supported schemes

```
<alias>:<tree-path>            # e.g. otherproj:<some-domain>/<some-leaf>.md
<alias>:thread/<slug>          # thread reference by alias
/<tree-path>                   # tree-internal path (same tree only)
file://<absolute-path>         # local file outside the tree
https://... | http://...       # web URL (PR, doc, article)
mcp://<server>/<resource>      # MCP-addressable resource (e.g. Slack thread)
```

### 5.2 Role vocabulary

```
spec                 # authoritative; agents should read fully
prior-decision       # pinned context; agents should read fully
related-work         # skim unless directly relevant
conversation         # source of origin; not authoritative
scratch              # working material
external-reference   # outside doc or article
```

Agents use `role` to budget context; humans use it to scan. Roles are advisory — the validator does not require them, but skills that materialize context will default-prioritize `spec` and `prior-decision` refs.

### 5.3 String sugar

For unrole'd references, a bare string is sugar for `{ uri: <string> }`:

```yaml
soft_links:
  - /<some-domain>/<some-leaf>.md          # sugar, tree-internal
  - uri: <alias>:<some-domain>/examples/   # object form, cross-project alias
    role: related-work
  - uri: mcp://slack/thread/C123/p456      # MCP ref with role
    role: conversation
```

---

## 6. NODE.md contract

Each tree directory is a node and has a `NODE.md` that:

1. Carries frontmatter per § 3.4.
2. Has an H1 matching the `title` field.
3. Has a `## Leaves` section listing every leaf file in this directory (as relative links).
4. Has a `## Sub-nodes` section if it has child directories.
5. Optionally has `## Overview` and `## Related` sections.

Leaves listed in `NODE.md` must exist on disk. Leaf files on disk not listed in `NODE.md` are `verify-tree` errors.

---

## 7. Multi-agent debate layout

Multi-agent debate runs against two artifact scopes: a **leaf** in the tree, or a **thread** during refinement. Both use the same on-disk layout and the same round protocol. The only difference is whether the artifact's `status` flips: leaves transition through `hardening` (§ 4.2), threads do not flip at all (§ 4.1).

Debate artifacts live in a `debate/` directory under the artifact's directory:

```
<artifact-dir>/                     # leaf-as-dir OR threads/<slug>/
  <artifact>.md                     # <leaf>.md or thread.md
  debate/
    index.md                        # rolling summary across rounds
    next-round-seed.md              # optional; carried from prior round-close
    round-01/
      feedback-in.md                # what this round should address (includes header: personas, review_mode, reviewers)
      baseline.md                   # optional; present iff review_mode == delta (captures the prior round's close state)
      personas.yaml                 # the resolved persona roster for this round (including ad-hoc ones)
      tryouts/
        <persona>.md                # per-reviewer analyses
      defender.md                   # rebuttal against reviewers
      synthesizer.md                # integrator (optional, for large rounds)
      proposed-patches.md           # concrete text ready to land
      open-issues.md                # carried forward to the next round
      transcript.md                 # round log
    round-02/
      ...
```

**Fixed roles** across every project:

- **Reviewer** (one or more; persona-specific; count controlled by `--reviewers=N`)
- **Defender** (exactly one; rebuts reviewer claims)
- **Synthesizer** (optional; integrates for large rounds)

**Persona sources.** Reviewer personas may be drawn from:

1. The project's § 10.2 roster (stable, re-usable; charters at `assets/persona-charters/<name>.md`).
2. Ad-hoc personas defined at round-open time via skill flags (one-off; charter captured in `personas.yaml` inside the round directory for audit).

Ad-hoc personas are round-scoped. They do not get added to § 10.2 automatically — if a user wants an ad-hoc persona to become permanent, they edit CONVENTIONS § 10.2 in a separate `chore(...)` commit.

**Review mode.** Each round declares its review mode in `feedback-in.md`:

- `full` (default) — reviewers read the entire artifact plus materialized context. Standard for round-01 and for any round after significant rewrites.
- `delta` — reviewers read `baseline.md` (the prior round's close state) plus the current artifact, and scope their analysis to what changed. Requires a prior closed round; refuses on round-01. Useful when a long artifact has had small targeted edits.

**Scope and status coupling:**

| Scope  | Artifact dir                     | Status flip | `status` field affected                 | Pointer field                                        |
|--------|----------------------------------|-------------|-----------------------------------------|------------------------------------------------------|
| leaf   | `<leaf-dir>/`                    | yes         | leaf `status`: `decided|specified ↔ hardening` | leaf `source_debate: debate/round-NN`         |
| thread | `threads/<slug>/`                | no          | thread `status` and `maturity` unchanged | thread `last_debate_round: debate/round-NN`         |

The `index.md` records per-round outcomes (patches accepted, defender verdicts like `CONCEDE / CONCEDE-IN-PART / DEFER / REJECT`, open issues carried forward) and the scope flag so a glance tells the reader whether the round was a hardening pass or a thread review.

---

## 8. Impl-specs

An impl-spec lives at `<leaf-dir>/impl-spec.md` and follows the six-section skeleton in `assets/impl-spec-template.md`:

```
1. Scope (in / out / deferred)
2. Interfaces
3. Acceptance tests
4. Build order
5. Known edge cases
6. Context refs
```

Once `derive-impl-spec` runs, the leaf frontmatter gets `impl_spec: impl-spec.md` and `status: specified`.

---

## 9. Invariants the validator enforces

`verify-tree` treats the following as errors. Identifiers **V-01 … V-22** match the detailed detection rules in `skills/verify-tree/SKILL.md`; the authoritative semantics live there, this section is the summary.

| ID    | Scope                | Summary                                                                                                                                          |
|-------|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| V-01  | every artifact       | `title` frontmatter equals the first H1 in the body.                                                                                             |
| V-02  | leaf, impl-spec      | `domain` frontmatter equals the leaf's actual parent tree path.                                                                                  |
| V-03  | every artifact       | Each `soft_links[].uri` resolves (tree-internal paths, project aliases; HTTPS URIs are only syntax-checked).                                     |
| V-04  | node directory       | Every `.md` file in a `tree/<domain>/` directory (aside from `NODE.md` and per-leaf debate / impl-spec sub-files) is listed in `NODE.md` → `## Leaves`. |
| V-05  | NODE.md              | Every leaf link in `NODE.md`'s `## Leaves` resolves to an existing file.                                                                          |
| V-06  | every artifact       | All required frontmatter fields per § 3.1 + type-specific section (§ 3.2–3.5) are present and non-empty (unless explicitly nullable).            |
| V-07  | thread               | `status` and `maturity` are consistent per § 4.1 (e.g. `in-review` requires `locking`; `archived` requires `maturity` absent).                    |
| V-08  | thread               | `len(promoted_to) == len(promoted_at)`.                                                                                                          |
| V-09  | leaf                 | Per-state transition invariants from § 4.2 (e.g. `specified` → impl_spec resolves to `status: ready`; `building` → impl_thread resolves to an active thread). |
| V-10  | NODE.md              | `status: decided`. Any other value is a violation.                                                                                                |
| V-11  | leaf + impl-spec     | `(leaf.status, impl-spec.status)` is consistent with § 4.4 (e.g. leaf `specified` → impl-spec `ready`; leaf `building` → impl-spec `building`).  |
| V-12  | thread               | Threads with `status: parked` have all three park fields (`parked_at`, `parked_by`, `parked_reason`) populated; non-parked threads have none.     |
| V-13  | leaf                 | Leaves with `status: hardening` have `pre_hardening_status ∈ {decided, specified}`; leaves with any other status have no `pre_hardening_status`. |
| V-14  | leaf (conditional)   | When a leaf's `source_thread` is set, the slug resolves to a thread in `threads/`, parked-thread locations, or `archive/`.                        |
| V-15  | any artifact         | The directed graph of `soft_links` (intra-tree edges only) is acyclic.                                                                             |
| V-16  | any artifact         | No `soft_links[].uri` resolves to the containing artifact itself.                                                                                  |
| V-17  | thread               | `promoted_to` entries are unique.                                                                                                                 |
| V-18  | thread               | `promoted_at` timestamps are monotonically non-decreasing.                                                                                         |
| V-19  | thread + leaf        | `debate/round-NN/` directories form a gap-free zero-padded sequence starting at `round-01`.                                                       |
| V-20  | leaf (conditional)   | When a leaf's `source_debate` is set, the path resolves to an existing `debate/round-NN/` directory.                                              |
| V-21  | any artifact         | Filenames under `project-brain/` match `^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)?$` (with exceptions for fixed names like `NODE.md`, `CONVENTIONS.md`, `README.md`, `thread.md`, `index.md`). |
| V-22  | artifact             | Artifact's frontmatter `source_thread` matches the parent thread slug on disk AND resolves to an existing thread in `threads/` or `archive/`. (See § 2.5.2.)                     |

The validator **does not** enforce the project-specific domain taxonomy in § 10.1 — projects can add their own checks by dropping a Python file into `scripts/verify-tree.d/` (see `skills/verify-tree/SKILL.md` § Extensions for the `check(brain, artifacts, violations)` contract).

---

## 10. Project-specific (fill in)

This is the only section a project customizes. Everything above is shared across all projects that install the pack.

### 10.1 Tree domain taxonomy

List the top-level domains this project uses. **The pack ships no domains by default** — whatever you write here, or whatever domain you supply at first `promote-thread-to-tree` invocation, is what `tree/` will populate.

> **Agents reading this section: do NOT copy any name shown below into a thread's `tree_domain`, into a staged path under `tree-staging/`, or into a `--allow-domain` flag. These are illustrations of *shape*, not real defaults. The user names their own taxonomy at promote-time. If you find yourself choosing a domain because it appeared in this doc, stop and ask the user via `AskUserQuestion`.**

Example shapes (these are SHAPES, not values to use — pick what fits the actual project):

```
# A backend-heavy software project might shape as:
<top-level-A>/
  <sub-A>/
  <sub-B>/
<top-level-B>/
<top-level-C>/

# A research project might shape as:
<methodology-folder>/
<findings-folder>/
<open-problems-folder>/

# A product-management project might shape as:
<discovery-folder>/
<shipping-folder>/
<post-mortems-folder>/
```

The pack's only constraint is § 11.1 (kebab-case slug). Names are entirely the user's call. The `promote-local.sh` script enforces this with a runtime guardrail: every promotion's destination domain must be **actively consented to** for that promotion — either via `tree_domain` on the thread's frontmatter (durable, survives sessions) or via `--allow-domain=<name>` on the script invocation (one-shot). Folder existence on disk is **not** consent — folders can get created by prior LLM mistakes, manual mkdir, or half-finished promotions, and silently re-using them would launder those into permanent destinations. The rule is universal — it doesn't single out specific names; "engineering" is no more refused than "kvasir-alpha-7", and a previously-used folder gets the same check as a brand-new one. The primary control is the HARD CONSTRAINT block in `skills/promote-thread-to-tree/SKILL.md` requiring agents to ask the user before staging; the script guardrail is the backstop that catches the agent when it skips the ask.

### 10.2 Debate personas

List the reviewer personas available to this project. The pack provides `defender` and `synthesizer` automatically.

```
- fresh-eyes-reader
- grammar-auditor
- phase-semantics-auditor
- cross-ref-auditor
- red-team
- ...
```

Each persona should have a brief (≤ 5 lines) charter describing what it looks for.

### 10.3 Build toolchain

Commands `ai-build` invokes.

```yaml
test: <command>
lint: <command>
build: <command>
```

### 10.4 Role vocabulary extensions (optional)

Projects may add roles beyond the § 5.2 defaults. If so, list them here so `materialize-context` and `verify-tree` recognize them.

---

## 11. Naming conventions

Skills share these naming rules. Deviation from reserved filenames or directory names is a `verify-tree` error; deviation from slug/branch/PR/commit style is a warning.

### 11.1 Slugs

Used as `id` in frontmatter, directory names under `threads/`, filenames for leaves, and in branch and PR construction.

- Lowercase, kebab-case.
- Characters: `[a-z0-9-]`. Must start with a letter. No leading or trailing hyphens; no double hyphens.
- Length: 3–40 characters. Short-and-memorable beats descriptive — the title carries the long form.
- Collision: if `<slug>` already exists, the skill that generated it appends `-2`, `-3`, … and asks the user to confirm.

### 11.2 Reserved filenames

Exact casing matters.

- `NODE.md` — tree node index (always capitalized).
- `thread.md` — thread root file.
- `CONVENTIONS.md` — this file, at the brain root (`project-brain/`).
- `decisions-candidates.md`, `open-questions.md`, `proposal.md`, `notes.md` — thread files.
- `feedback-in.md`, `defender.md`, `synthesizer.md`, `transcript.md`, `proposed-patches.md`, `open-issues.md` — debate round files.
- `impl-spec.md` — implementation spec inside a leaf directory.
- `thread-index.md`, `current-state.md` — global thread registry and snapshot.

### 11.3 Directory names

All lowercase. Reserved: `thoughts`, `threads`, `archive`, `tree`, `tree-staging`, `debate`, `tryouts`, `diagrams`.

Debate round directories are zero-padded two-digit: `round-01`, `round-02`, …, `round-99`. Must be sequential — gaps are a validator error.

### 11.4 Branches

- `promote/<thread-slug>` — promotion PR branch. One thread typically produces one promotion branch per wave. If a thread is split across multiple PRs in the same wave, suffix: `promote/<thread-slug>/<topic>` (e.g. `promote/adp-ir-2026-04/runtime-contract`). If the thread cycles and re-promotes, suffix with wave number: `promote/<thread-slug>-2`, `-3`.
- `build/<leaf-slug>` — implementation PR branch (code repo, which may be different from the brain repo).
- `chore/<short-description>` — convention updates, tree hygiene.
- `thread/<thread-slug>` — reserved for the rare case where thread work itself needs a branch; most thread work happens on `main`.

**Base branch selection.** Promotion branches are cut from whichever base branch the promote PR targets, not a hard-coded `origin/main`. The skill resolves the base in this order:

1. Explicit `--base=<branch>` flag.
2. Prompt the user, defaulting to the `default_base` of the selected remote (§ 2).

Enforced by `promote-thread-to-tree` at branch creation. The same rule applies to `build/<leaf-slug>` — code PRs frequently target release trains or integration branches rather than `main`.

### 11.5 PR titles

- Promotion: `promote: <Thread Title> → <domain>`
- Build: `build: <Decision Title> [<leaf-slug>]`
- Debate patch round: `debate: <leaf-slug> round-NN patches`
- Convention / hygiene: `chore: <description>`

### 11.6 Commit messages

Conventional commits with thread or leaf scope:

```
<type>(<scope>): <subject>
```

- `<type>`: one of `promote | build | debate | chore | docs`.
- `<scope>`: thread slug for thread work; leaf slug for build or debate work; tree path fragment for hygiene commits.
- Subject: imperative, sentence case, no trailing period. Body (optional) wraps at 72 chars.

Examples:

```
promote(<thread-slug>): add <leaf-slug> to <domain>/<sub>
debate(<thread-slug>): round-05 proposed patches
build(<leaf-slug>): stage 2 — validator surface
chore(tree): normalize soft_links under <domain>/
```

---

## 12. Audit log (stub)

**Status: specification only. v1.0 feature.** The full spec lives in `AUDIT-LOG.md` at the pack root.

Every mutating skill in the pack will (in v2.x) append a one-line JSONL record to `project-brain/.audit-log.jsonl` capturing the invocation: who, when, what, which artifacts, which commit, with what flags. Complements git history.

Schema summary:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | int | yes | Always 1 for v1.0. |
| `ts` | string (ISO-8601 UTC) | yes | Invocation completion time. |
| `skill` | string | yes | Skill name (e.g. `promote-thread-to-tree`). |
| `skill_version` | string | yes | SKILL.md version at invocation. |
| `op` | string | yes | Operation tag (e.g. `promote`, `park`, `finalize`). |
| `actor` | string | yes | Resolved user (git config, frontmatter, or CLI). |
| `dry_run` | bool | yes | Whether `--dry-run` was set. |
| `exit` | int | yes | Exit code (0 success, 1 expected failure, 2 unexpected error). |
| `artifacts` | array of strings | yes | Relative paths touched. Empty on dry-run or pre-flight exit. |
| `commit` | string &#124; null | yes | Commit SHA or null if no write. |
| `flags` | object | yes | Resolved flag map (secrets redacted). |
| `details` | object | no | Skill-specific extras (e.g. `merged_pr_url`, `round_number`). |

Invariants:

- Append-only: entries are never modified or deleted, only appended.
- Redacts secret-pattern values in `flags` (e.g. API keys, credentials) as `***` to protect against accidental commit.
- Write failure never aborts the primary operation — auditing is advisory, not critical.
- Tracks both successes (exit 0) and expected failures (exit 1) so the log captures access patterns and precondition violations.

See `AUDIT-LOG.md` for the full spec, implementation plan, and open questions.

---

## Appendix A — Changelog

- **1.0.0-rc4** (unreleased) — One breaking directory rename plus five additive quality-of-life shifts driven by agentic-IDE usability feedback:
  1. **Brain directory renamed**: `thoughts/` → `project-brain/` for namespace clarity (a first-time viewer opening a repo now sees a directory name that unambiguously identifies the owning tool). Per-brain migration: `git mv thoughts project-brain` then run `scripts/migrate-brain-dir.sh` to sweep path literals inside the migrated brain. `RESERVED_DIRS` keeps `"thoughts"` alongside `"project-brain"` so a half-migrated repo is diagnosed with N-03 rather than silently re-accepted.
  2. **Two-layer alias registry** (§ 2): per-project `<brain>/config.yaml` is now authoritative for alias resolution; the user-global registry moves from `~/.ai/projects.yaml` to `~/.config/project-brain/projects.yaml` (XDG-compliant) and is opt-in. A brain that never references another project needs neither file. V-03 severity rules adjusted: *warning* when no layer present (brain remains usable), *error* when a layer exists but the alias is missing. The pack is fully functional without any `~/` access.
  3. **Operational config** (§ 2.5): `verbosity: terse|normal|verbose` (default `terse`) and `transcript_logging: on|off` (default `on`) now live in `<brain>/config.yaml`. Env overrides: `PROJECT_BRAIN_VERBOSITY`, `PROJECT_BRAIN_TRANSCRIPT`. Skills that previously narrated every tool call default to a short acknowledgement + `Done.` line. Each SKILL.md carries a `### Verbosity contract` section declaring what each level emits.
  4. **Per-thread transcript + attachments** (§ 1): `transcript.md` (append-only human-LLM log) and `attachments/` (intermediates — screenshots, scratch md, etc.) are now first-class thread-directory entries, exempt from V-06 frontmatter rules via `KINDS_WITHOUT_FRONTMATTER`. Both are gitignored by default so PR history doesn't balloon; users opt in by deleting the gitignore lines. `transcript.md` is added to `RESERVED_FILENAMES` and `attachments` to `RESERVED_DIRS`.
  5. **Git dependency deferred to promote-time**: pre-promote skills (capture, refine, park/unpark, debate, decide, specify, harden, triage, query, materialize-context) no longer shell out to git — they are pure file operations. Only the `promote-thread-to-tree` / `finalize-promotion` / `discard-promotion` triad retains git calls. `init-project-brain`'s `git init` is now opt-in via `--init-git`. Inside agentic IDEs this removes a permission prompt per tool call during the majority-case thread lifecycle.
  6. **`init-project-brain` reduced to zero interactive questions by default** with smart-derived values: alias = slugified directory name, title = title-cased directory name, owner = `git config user.email` (fallback `$USER@localhost`). `--interactive` flag restores prompting. `--init-git`, `--brain-path <path>`, `--no-registry` flags cover the other modes.
  - Validator collateral: new `scripts/verify_tree/config.py` (two-layer resolver — `per_project_config_path`, `global_registry_path`, `resolve_alias`, `any_layer_available`, `get_verbosity`, `get_transcript_policy`). V-03 rewired to consume it. `KINDS_WITHOUT_FRONTMATTER` gains `transcript` + `attachment`. `discovery.classify()` recognizes `transcript.md` and files under `<thread>/attachments/`. 5 new `V2AdditionsTests` in the unit suite (49 total, all green). Honours `PROJECT_BRAIN_CONFIG` and `PROJECT_BRAIN_PROJECTS_YAML` env overrides for tests/CI.
- **0.9.0-alpha.4** (unreleased — Stage 4 of v0.9.0 cut, audit-log stub + docs polish) — Added § 12 Audit log (stub) pointing to `AUDIT-LOG.md` at the pack root. Specification-only: the schema and integration contract for a per-skill-invocation JSONL log at `thoughts/.audit-log.jsonl`. No new invariants; wiring is planned for v1.0. Also landed pre-release polish: § 9 was expanded from the original 11-row summary into the full V-01..V-21 invariant table that matches `skills/verify-tree/SKILL.md` (no semantic change — verify-tree's SKILL.md remains the source of truth; § 9 is now a faithful summary). Patch bumps on three triage skills to close missing contract-template sections without behavior change: `discover-threads` → 0.1.1 (added `Side effects` / `Frontmatter flips` / `Asset dependencies`; also normalized `## Inputs` heading and ordered `## Postconditions` before `## Failure modes` per template), `review-parked-threads` → 0.1.1 (added `Side effects` / `Outputs` / `Frontmatter flips` / `Asset dependencies`; same heading/ordering normalization), `assign-thread` → 0.1.3 (added `Asset dependencies`). The four thread-level writers (`new-thread` / `update-thread` / `park-thread` / `discard-thread` all at 0.2.2) had their `### Dry-run semantics` exit-code contracts documented as the uniform `0 / 1 / 2` set, matching the other five dry-run-capable skills. Root `README.md` frames `--dry-run` support as "all nine operational write skills" with an explicit carve-out for `init-project-brain` (one-time, idempotent, `mkdir`-shaped setup guarded by refuse-if-exists), and lists only `derive-impl-spec` and `ai-build` as v1.0 deferrals. Housekeeping files introduced: `LICENSE` (Apache-2.0), `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, `.gitignore`, `.github/workflows/verify-brain.yml`. v0.9.0 ships with the stub so projects can wire their own audit hooks against a stable schema.
- **0.9.0-alpha.3** (unreleased — Stage 3 of v0.9.0 cut) — Discovery, assignment, and triage skills that exercise the alpha.2 team fields. Three new skills land, all at version 0.1.0; no schema changes, no invariant changes, no template changes.
  - `discover-threads` (new, 0.1.0) — read-only fleet query. AND-style filter set over thread frontmatter: `--status`, `--assigned`, `--owner`, `--maturity`, `--domain`, `--modified-before`, `--modified-after`, `--review-requirement`, `--has-pr`, `--unpark-trigger-set`. Output formats: `table` (default), `json`, `csv`, `yaml`, `paths`. No writes, no frontmatter flips. Exercises the `assigned_to` and `review_requirement` fields from alpha.2 as first-class filter inputs without implying a policy model.
  - `assign-thread` (new, 0.1.0) — mutates a thread's `assigned_to` list. Operations: `--add <handle>`, `--remove <handle>`, `--set <handle>[,<handle>...]`, `--clear`. Appends an audit line (`YYYY-MM-DD — <actor> — <op>: <handles>`) to the thread body's `## Assignment history` section (creates the section if absent) and calls `verify-tree --rebuild-index` as the final step so the aggregate index files pick up the change in the same commit. Does not enforce an assignment model — accepts whatever handles the project uses (GitHub, Slack, email).
  - `review-parked-threads` (new, 0.1.0) — read-only triage report over `status: parked` threads. Partitions the fleet into three categories: **actionable** (`unpark_trigger` set), **stale** (`parked_at` older than `--stale-days`, default 90), and **no-trigger hygiene** (parked without `unpark_trigger`). Default output is `markdown-report` for direct consumption; `json` and `table` also available. Pure query — no writes, no lifecycle flips; recommends `park-thread --unpark`, `discard-thread`, or `update-thread` as follow-ups without invoking them.
  - Integration: README skill table grows from 11 to 14 rows; no new invariants because the underlying fields (`assigned_to`, `review_requirement`, `parked_at`, `unpark_trigger`) already shipped with their own V-NN coverage in prior alphas. No changes to CONVENTIONS § 3 (schema), § 4 (lifecycles), § 7 (debate), § 9 (invariants), § 11 (naming), or the assets directory.
- **0.9.0-alpha.2** (unreleased — Stage 2 of v0.9.0 cut) — Shared-index refactor + optional team-oriented fields. `thread-index.md` and `current-state.md` shifted from hand-edited primary artifacts to autogenerated projections of per-thread `thread.md` frontmatter. New § 1.1 documents the source-of-truth model and the merge-conflict resolution procedure (accept either side + `verify-tree --rebuild-index`). Two new optional § 3.2 thread fields: `assigned_to` (free-form list of owner/collaborator handles) and `review_requirement` (free-form review-policy string). Both are intentionally unenforced by the pack — policy and assignment models are team-specific and wired externally via CODEOWNERS, branch protection, or team tooling. Skill-level changes: `verify-tree` → 0.3.0 (new `--rebuild-index` mode with deterministic, atomic regeneration of both index files; exit codes 0/1/2; `--dry-run` compatible; contract section documenting what mutating skills must do); `new-thread`, `update-thread`, `park-thread`, `discard-thread`, `discard-promotion` → 0.2.0, `promote-thread-to-tree`, `finalize-promotion` → 0.3.0 — each removed its inline edits to the aggregate index files and added a final "rebuild indexes" step invoking `verify-tree --rebuild-index` before commit, along with two new failure modes (rebuild source-validation failure, rebuild write failure). Asset templates (`thread-index-template.md`, `current-state-template.md`) gained an `AUTO-GENERATED` HTML-comment header; `thread-template/thread.md` gained commented-out stubs for the two new optional fields. No change to invariant set; V-01..V-21 from alpha.1 unchanged.
- **0.9.0-alpha.1** (unreleased — Stage 1 of v0.9.0 cut) — Safety & correctness hardening landed across four skills plus the validator. No schema changes in this stage; all existing fields/invariants remain. Skill-level changes:
  - `multi-agent-debate` → 0.3.0: path-traversal guard on `--artifact-path` (refuses canonical paths outside `brain_path`); persona charter now wrapped in a fixed ADVISORY envelope before being handed to reviewer subagents so injected override instructions are framed as data; persona-charter linter scans charters for override phrases (`ignore prior instructions`, `approve everything`, `bypass`, `jailbreak`, …) and warns without blocking; new "Security" section summarizing defense-in-depth. Personas remain free-form per user direction; defenses are mitigations, not guarantees.
  - `materialize-context` → 0.2.0: path-traversal guard on `--artifact-path`, `--out`, and `--persist` targets; resolved URI content now enclosed in HTML-comment fences (`<!-- BEGIN RESOLVED CONTENT from <uri> ... -->` / `<!-- END RESOLVED CONTENT ... -->`) so downstream consumers treat the content as data, not instructions; visible `--persist` privacy warning reminding users that `mcp://`/`https://` content should be covered by `.gitignore`; optional `--strict` flag to escalate the warning into a refusal.
  - `promote-thread-to-tree` → 0.2.0: secret-pattern precondition scans thread and `tree-staging/` for `.env*`, `*.key`, `*.pem`, `*.p12`, `*.pfx`, `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`, `secrets.{yaml,yml,json}`, `credentials.{yaml,json}`, `*.gpg`, `*.enc`, refusing promotion with an actionable file list; `--allow-secrets` expert-mode escape emits a warning. Working-tree cleanliness check widened from `project-brain/`-scoped to full-repo `git status --porcelain` so stray staged changes in unrelated paths are caught before the promote branch is cut.
  - `finalize-promotion` → 0.2.0: new pre-commit step re-reads thread frontmatter from disk and refuses if `tree_prs[-1]` already appears in `promoted_to` (concurrent-finalize guard); precondition 7 now verifies leaf `status: in-review` on the merge commit itself (`git show <merge-sha>:<leaf-path>`) rather than the promote branch's HEAD, defending against rebase/force-push that strips the flip-to-in-review commit.
  - `verify-tree` → 0.2.0: invariant set expanded from V-01..V-11 to V-01..V-21. V-12 (parked-thread required-field completeness) and V-13 (hardening `pre_hardening_status` presence + value constraint) land the previously-acknowledged gaps. New invariants: V-14 dangling `source_thread`, V-15 `soft_links` DAG check (DFS cycle detection, intra-tree edges only), V-16 `soft_links` self-reference ban, V-17 `promoted_to` uniqueness, V-18 `promoted_at` monotonic non-decreasing, V-19 debate round sequentiality (`round-NN` no gaps), V-20 dangling `source_debate`, V-21 ASCII-only filename constraint under `thoughts/` with exemptions for fixed special names. No new schema fields required.
  - No change to CONVENTIONS schema in this stage; stage-2 (shared-index refactor + optional `assigned_to` / `review_requirement` fields) and stage-3 (discovery + assignment skills) will bump the schema.
- **0.8.0** (2026-04-22) — Multi-agent debate scope expansion. § 7 generalized: debate may now run against either a leaf (as before, with `status: decided|specified ↔ hardening`) or a thread (during refinement, no status flip, any number of rounds). Round layout unchanged; `personas.yaml` and optional `baseline.md` added to the round directory to capture ad-hoc persona charters and delta-review baseline. New optional § 3.2 thread field `last_debate_round` — pointer to the most recent round (persists across close). § 4.1 notes that thread-scope debate does not change `status` or `maturity`. § 7 documents the three new skill parameters: `--reviewers=N` (configurable reviewer count), `--review-mode=full|delta`, and `--personas` with both § 10.2-referenced and ad-hoc personas. No invariant changes.
- **0.7.0** (2026-04-22) — Pre-promotion thread operations plus multi-agent debate schema. Added `parked` as a first-class thread status (§ 4.1) for threads paused without archiving; `active ↔ parked` cycle owned by `park-thread` / `park-thread --unpark` with maturity preservation. Added `update-thread` (structured edits on `active` or `parked` threads — no status change) and `discard-thread` (direct `active|parked → archived` when `tree_prs` is empty) to § 4.1. New optional § 3.2 fields: `parked_at`, `parked_by`, `parked_reason`, `unpark_trigger`, `discard_reason`. New optional § 3.3 leaf field `pre_hardening_status` — transient, written by `multi-agent-debate` on round open to record the pre-hardening state so round close can restore it; present iff `status == hardening`. Invariants unchanged — existing rules about `maturity != locking` when archiving still hold; `discard-thread` refuses rather than coercing the maturity field.
- **0.6.0** (2026-04-22) — Added `archived_at` and `archived_by` optional thread frontmatter fields (§ 3.2). Populated by `finalize-promotion` when the archive disposition is chosen, or by the author on manual archive. Absent on active or in-review threads. Enables `thread-index.md`'s Archived table to render without parsing git log.
- **0.5.1** (2026-04-22) — Lifecycle attribution fixes. § 4.1 `active/refining` re-entry and `archived` rows now credit `finalize-promotion` (not `promote-thread-to-tree`, which ends at PR open). § 4.2 `decided` row same fix. Acknowledges `discard-promotion` as the still-unbuilt skill for PR-closed-without-merge.
- **0.5.0** (2026-04-22) — Remote + base-branch model. § 2 `projects.yaml` schema gains a `remotes:` list (each entry has `name`, `url`, `default_base`) plus `default_remote`. Single-remote is the common case but the list form is required for schema uniformity. § 11.4 clarifies that promote branches are cut from whichever base the PR targets, not hard-coded `origin/main`; skill prompts per thread since threads within one project routinely land on different branches. No change to `tree_prs` shape — PR URL encodes remote and base for audit.
- **0.4.0** (2026-04-21) — Brain root moved from `<project>/.ai/` to `<project>/thoughts/`. Deliberate un-hiding: the brain is content, not config. Removed the intermediate `.ai/thoughts/` layer; `threads/`, `tree/`, `archive/`, `thread-index.md`, `current-state.md`, and `CONVENTIONS.md` all now live directly under `thoughts/`. `brain:` paths in `~/.ai/projects.yaml` updated accordingly. User-global registry at `~/.ai/projects.yaml` unchanged (it remains hidden config).
- **0.3.1** (2026-04-21) — Added § 3.5 impl-spec frontmatter schema (`kind: impl-spec`, `source_leaf`, `source_debate`).
- **0.3.0** (2026-04-21) — Added § 11 naming conventions (slugs, reserved filenames, directory names, branches, PR titles, commit messages).
- **0.2.0** (2026-04-21) — Lifecycle revisions. Dropped `decided` from thread states; threads now cycle `active ↔ in-review → archived`. `tree_pr` → `tree_prs` (list); `promoted_to` / `promoted_at` now parallel lists. `hardening` clarified as transient enterable from `decided` or `specified`. Added NODE.md lifecycle (§ 4.3). Added impl-spec lifecycle as independent from leaf lifecycle with coupling table (§ 4.4). Added "flipped by" column to lifecycle tables. Added per-state transition invariants to validator rules.
- **0.1.0** (2026-04-21) — initial draft.
