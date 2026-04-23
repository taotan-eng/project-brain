# Release Notes

## v1.0.0-rc4 — 2026-04-23

**One breaking directory rename** plus five additive quality-of-life shifts driven by agentic-IDE usability feedback. Migrate an existing rc3 brain with the helper script (below).

### Summary

| Shift | What changed |
|---|---|
| Brain directory renamed | `thoughts/` → `project-brain/` for namespace clarity. `RESERVED_DIRS` still recognizes `thoughts/` so half-migrated brains are diagnosed with N-03 rather than silently re-accepted. |
| Two-layer alias registry | Per-project `<brain>/config.yaml` is authoritative; `~/.config/project-brain/projects.yaml` (moved from `~/.ai/projects.yaml`) is opt-in. Brain works with neither file. |
| Operational config | `verbosity` (default `terse`) + `transcript_logging` (default `on`) in `<brain>/config.yaml`. Env overrides available. |
| Per-thread transcript + attachments | `<thread>/transcript.md` (append-only log) and `<thread>/attachments/` (intermediates). Both gitignored by default. |
| Git deferred to promote-time | Pre-promote skills are pure file ops. Git only at `promote-thread-to-tree` / `finalize-promotion` / `discard-promotion`. `init-project-brain`'s `git init` is opt-in. |
| `init-project-brain` zero-Q&A | Smart-derived alias/title/owner by default. `--interactive` flag to restore prompting. |

### Migration from rc3

```sh
cd <your project>
bash path/to/project-brain-pack/scripts/migrate-brain-dir.sh
# review the diff, then:
git add -A && git commit -m "migrate brain dir to rc4 layout"
```

The helper script:

- `git mv thoughts project-brain` (preserves history when the brain is in a git repo; plain `mv` otherwise)
- Sweeps path literals `thoughts/` → `project-brain/` inside markdown + yaml files in the migrated brain
- Sweeps `~/.ai/projects.yaml` → `~/.config/project-brain/projects.yaml` in any lingering references
- Writes a minimal `<brain>/config.yaml` stub if one doesn't exist
- Appends v2 transcript + attachments gitignore defaults to `.gitignore`
- Runs the validator to confirm the migrated brain validates clean

What the script does NOT do:

- Move `~/.ai/projects.yaml` to `~/.config/project-brain/projects.yaml`. You do that yourself, and only if you use cross-project soft-links at all. A brain that doesn't reference other projects needs no registry.
- Commit the changes. Review the diff, then commit yourself.

### Detail per shift

**1. Brain directory renamed: `thoughts/` → `project-brain/`**

Driver: namespace clarity. Before rc4 a user opening a project repo saw a directory called `thoughts/` — generic enough that another AI tool could plausibly claim the same name. `project-brain/` is unambiguous. CONVENTIONS.md and every example in the pack now describe the brain root as `project-brain/`. The validator keeps `"thoughts"` in `RESERVED_DIRS` for back-compat — a repo that contains both is flagged with N-03.

**2. Two-layer alias registry**

CONVENTIONS § 2 rewritten. Alias lookup now consults:

1. Per-project `<brain>/config.yaml` `aliases:` block — authoritative.
2. User-global `~/.config/project-brain/projects.yaml` — opt-in fallback. XDG-compliant (honours `$XDG_CONFIG_HOME`).

V-03 severity:

- **No layer present** → warning. The brain is usable; cross-project refs are just unverified.
- **Some layer present but alias missing** → error (the author declared they use a registry but forgot this alias).
- **Alias resolves but target doesn't exist** → error.

Env overrides for tests/CI: `PROJECT_BRAIN_CONFIG`, `PROJECT_BRAIN_PROJECTS_YAML`.

**3. Operational config**

New per-project config at `<brain>/config.yaml`. Schema:

```yaml
primary_project: my-app
aliases:
  otherproj:
    brain: /path/to/other/project-brain
verbosity: terse               # terse (default) | normal | verbose
transcript_logging: on         # on (default) | off
```

Verbosity:

- **terse** (default): one acknowledgement line + `Done.` No tool-output echo, no "let me..." preamble.
- **normal**: structured summary of what changed, no conversational framing.
- **verbose**: full narration (pre-rc4 default). Useful for debugging.

Every SKILL.md has a `### Verbosity contract` section documenting what each level emits for that specific skill.

**4. Per-thread transcript + attachments**

Two new thread-directory entries:

- `<thread>/transcript.md` — append-only verbatim human-LLM log. `thread.md` remains the curated summary.
- `<thread>/attachments/` — intermediates produced during a session (screenshots, scratch md, diagrams, tryout scripts).

Both exempt from V-06 frontmatter rules via `KINDS_WITHOUT_FRONTMATTER`. Gitignored by default — the durable record is `thread.md`, and transcripts bloat PR history. Opt in by removing the gitignore lines.

Per-thread override: thread frontmatter `transcript: off` disables transcript logging for that thread.

**5. Git deferred to promote-time**

Pre-promote skills no longer invoke git. They are pure file operations. Affected skills:

- new-thread, update-thread, park-thread, discard-thread
- multi-agent-debate, assign-thread
- discover-threads, review-parked-threads (read-only)
- materialize-context
- verify-tree

Git still lives in the three promote-time skills, which legitimately need to branch / commit / push / open PRs:

- promote-thread-to-tree, finalize-promotion, discard-promotion

Rationale: inside agentic IDEs, pre-promote git calls trigger a permission prompt per tool call. That friction drove the separation. Users commit their own local work whenever they want.

`init-project-brain`'s `git init` is now opt-in via `--init-git`. Default install creates the brain dir without touching git.

**6. `init-project-brain` zero Q&A**

Default invocation asks zero interactive questions. Smart-derived values:

- `alias` — slugified directory name (`My App` → `my-app`)
- `title` — title-cased directory name
- `owner` — `git config user.email`; falls back to `$USER@localhost`

Output: one line.

```
Initialized project-brain in ./project-brain/ (alias: my-app, owner: alice@example.com).
```

Flags:

- `--interactive` — walk through the three required values plus an optional registry prompt.
- `--init-git` — run `git init` + scaffold commit.
- `--brain-path <path>` — override the default `./project-brain/` location.
- `--no-registry` — skip any global-registry integration.

### Validator changes (`scripts/verify_tree/`)

- New `config.py` module: `per_project_config_path`, `global_registry_path`, `resolve_alias`, `any_layer_available`, `get_verbosity`, `get_transcript_policy`.
- `model.py`: added `transcript` + `attachment` to `KINDS_WITHOUT_FRONTMATTER`; added `transcript.md` + `config.yaml` to `RESERVED_FILENAMES`; added `project-brain` + `attachments` to `RESERVED_DIRS` (kept `thoughts` for half-migrated-repo back-compat).
- `discovery.py::classify()` recognizes `transcript.md` (kind=`transcript`) and any file under `<thread>/attachments/` (kind=`attachment`).
- `invariants_refs.py`: V-03 rewired to call `config.resolve_alias` with two-layer semantics.
- Unit suite: 49 tests (up from 44). New `V2AdditionsTests` class covers transcript kind, attachment kind, V-03 two-layer resolution (no-layer / per-project-hit / layer-present-but-missing cells).

### CI

`.github/workflows/verify-brain.yml`:

- Triggers on `project-brain/**`, `thoughts/**`, `skills/**`, `scripts/**`, `CONVENTIONS.md`. Both brain-dir names are watched so a half-migrated repo still triggers CI.
- Runs the validator against `project-brain/` if present; falls back to `thoughts/` with a migration-nudge warning; skips with a message in pack-only repos.
- Runs the unit suite via `python3 -m unittest discover` (carries the rc3 CI fix of dropping broken `cache: 'pip'`).

### Known gaps in this rc

- Skill prompts enforce the verbosity contract by instruction, not by runtime. LLM adherence is approximately 80%. Expect stray prose in terse mode occasionally until prompts settle in subsequent rcs.
- Transcript format is human-readable `transcript.md` per product decision. Machine-re-ingestion tooling (parsing transcripts back into context) is future work.
- E2E sandbox driver regen against the new config + transcript + attachments flow + renamed directory is not yet run against this rc. Unit suite is clean; E2E rerun recommended before rc5.

### Shipping

```bash
cd <pack-repo>
git add -A
git commit -m "v1.0.0-rc4: rename thoughts/ to project-brain/ + two-layer config + git deferral + transcript + verbosity + zero-Q&A init"
git tag -a v1.0.0-rc4 -m "v1.0.0-rc4"
git push origin main
git push origin v1.0.0-rc4
```

---

## v1.0.0-rc3 — 2026-04-22

(See git log for v1 history.)
