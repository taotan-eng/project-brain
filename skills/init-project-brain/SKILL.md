---
name: init-project-brain
description: One-time scaffold of the project-brain skeleton into a git repo. Default invocation: zero interactive questions. Alias=slugified dir name, title=title-cased dir name, owner=git config user.email. Creates project-brain/ with CONVENTIONS.md, tree/NODE.md, empty threads/ and archive/. Optional --interactive flag prompts for all values. Optional --init-git runs git init + scaffold commit. Appends alias entry to ~/.config/project-brain/projects.yaml. Use when the user says "set up project brain", "install project-brain here", or adopts this pack in a new repo first time.
version: 1.0.0-rc4
pack: project-brain
requires:
  - git
  - "read:pack/CONVENTIONS.md"
  - "write:[project-root]"
  - "write:~/.config/project-brain/projects.yaml"
---

# init-project-brain

Turns a plain git repository into a project-brain-enabled one. Before this skill runs, there is no place for threads to live and no tree structure for decisions to land in; after it runs, every other skill in the pack has its preconditions met. This is the first skill a user invokes when adopting the pack in a new project.

The skill is deliberately opinionated at a few points: it pre-scaffolds top-level domain directories from § 10.1, it always copies a fresh `CONVENTIONS.md` (so the project starts on the pack's current version, not a stale one), and it writes a single bootstrap commit so the entire scaffold lands as one reviewable unit. Sub-domains and the leaves inside them emerge later via `promote-thread-to-tree`.

## When to invoke

- "Set up project brain" / "install project-brain here" / "init the brain"
- First-time adoption of the pack in a repository
- After a team votes to standardize on this pack and needs the baseline scaffolded
- **Do not use** to repair or migrate an existing brain — that's a separate skill (not yet drafted: `repair-brain` / `migrate-brain`).

## Inputs

| Name                | Source                          | Required | Description                                                                               |
|---------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------|
| `project_alias`     | user prompt                     | yes      | Kebab-case key for `~/.config/project-brain/projects.yaml` (§ 11.1). Must not already exist in the registry. |
| `project_title`     | user prompt                     | yes      | Human-readable name used in `thread-index.md` and `current-state.md` headers.             |
| `brain_path`        | user prompt (default = cwd)     | yes      | Absolute path where `project-brain/` is to live. Defaults to `<cwd>/thoughts`.                 |
| `remotes`           | `git remote -v` + user prompt   | yes      | List of remotes the brain repo may push to. Detected from git; user confirms each entry.  |
| `default_remote`    | user prompt                     | conditional | Required when `remotes` has >1 entry; defaults to the sole entry otherwise.            |
| `default_base_per_remote` | user prompt               | yes      | Per-remote default base branch (usually `main` or `master`). One value per remote.        |
| `domain_taxonomy`   | user prompt                     | yes      | § 10.1 top-level domains as a line-separated list (e.g. `engineering / product / operations`). 1–8 entries. |
| `debate_personas`   | user prompt                     | no       | § 10.2 reviewer personas. Default empty — easy to add later by hand-editing `CONVENTIONS.md`. |
| `build_toolchain`   | user prompt                     | no       | § 10.3 test/lint/build commands. Default empty.                                           |
| `owner`             | `git config user.email`         | yes      | Who ran init; recorded in the bootstrap commit.                                           |

**Zero-Q&A defaults (new in v1.0.0-rc4):**
- `project_alias`: kebab-case slug of current directory name (e.g., `My App` → `my-app`). Validated per § 11.1.
- `project_title`: title-cased directory name (e.g., `my-app` → `My App`).
- `owner`: `git config user.email`, falls back to `$USER@localhost` if empty. When the fallback is used, the skill writes a visible TODO marker into CONVENTIONS.md § 10 (see Process step 4) so the user sees it on first open of the file — fixing it later is one edit, not a hunt.
- `domain_taxonomy`: `engineering`. A single default domain. User adds more by hand-editing CONVENTIONS.md § 10.1 or re-runs with `--interactive`.

**Prompt strategy:** Default invocation asks zero interactive questions. With `--interactive` flag, one call collects `project_alias` + `project_title` + `domain_taxonomy`. Remote/base confirmation and persona/toolchain setup happen only with `--interactive`.

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a git repository (`git rev-parse --is-inside-work-tree` returns `true`).
2. The target `brain_path` does not already exist. If it does, refuse — direct the user at a hypothetical `repair-brain` or ask them to move the existing directory first.
3. Working tree is clean on `main` (or the project's default branch). Init commits directly to that branch; uncommitted changes would be swept into the bootstrap commit.
4. `git config user.email` returns a value.
5. `~/.config/project-brain/projects.yaml`, if it exists, does **not** already contain `project_alias`. If it does, prompt — suggest a suffixed alias (`<alias>-2`) or ask the user to pick a different one.
6. `git remote -v` returns at least one remote, OR the user explicitly confirms offline-only scaffolding (no push, no remote entry in `projects.yaml`).
7. Each entry in `domain_taxonomy` matches the slug rules of § 11.1 (kebab-case, no sub-paths — sub-nesting emerges through promotion, not init).

## Process

Each step is atomic. A failure at step N leaves the filesystem in whatever state it was after step N-1; no partial scaffolds are left committed.

1. **Resolve inputs.** If `--interactive` is set, prompt for all values (project_alias, project_title, domain_taxonomy, remotes/bases, personas, toolchain). Otherwise, apply zero-Q&A defaults: derive alias and title from directory name, set owner from git config, set domain_taxonomy to `[engineering]`. Store inferred `brain_path` as `<cwd>/project-brain` or explicit `--brain-path` value.
2. **Validate preconditions.** Run checks 1–7. On failure, stop and report the specific precondition.
3. **Create brain directory.** `mkdir -p <brain_path>/tree <brain_path>/threads <brain_path>/archive`.
4. **Write `CONVENTIONS.md`.** Read the pack's canonical `CONVENTIONS.md` (the one this pack ships). Splice § 10 subsections with the user's answers:
    - § 10.1 Tree domain taxonomy — replaced with the `domain_taxonomy` list as a fenced-block outline.
    - § 10.2 Debate personas — replaced with `debate_personas` if provided; otherwise keep the placeholder with a "— TBD; add personas before invoking `multi-agent-debate`" comment.
    - § 10.3 Build toolchain — replaced with `build_toolchain` if provided; otherwise leave as commented placeholders.
    - § 10.4 — untouched unless `role_extensions` was volunteered (rare at init time).
    - **Owner TODO marker (v1.0.0-rc4).** If the resolved `owner` is the `$USER@localhost` fallback (because `git config user.email` was unset or empty), prepend a visible HTML comment block to § 10 that reads:
      ```
      <!-- TODO(project-brain init): The brain was scaffolded with owner = "<$USER>@localhost"
           because `git config user.email` was unset. Replace every `owner: <$USER>@localhost`
           reference in this brain (CONVENTIONS.md, any thread.md, the ~/.config/project-brain
           registry entry if present) with your real email, then delete this TODO block. -->
      ```
      When the owner is a real email from git config, do NOT emit this block. The marker must be impossible to miss: first thing inside § 10, before § 10.1.
   Write to `<brain_path>/CONVENTIONS.md`. Do not modify the sections above § 10 — those are the pack's shared contract.
5. **Scaffold the root NODE.md.** Copy `assets/NODE-template.md` to `<brain_path>/tree/NODE.md`. Fill placeholders: `{{TITLE}}` = `"<project_title> — Knowledge Tree"`, `{{DOMAIN}}` = `/`, `{{PRIMARY_PROJECT}}` = `project_alias`. Populate the `## Sub-nodes` section with one bullet per entry in `domain_taxonomy`, each linked to the sub-directory's `NODE.md`.
6. **Scaffold per-domain NODE.md.** For each `<domain>` in `domain_taxonomy`:
    - `mkdir -p <brain_path>/tree/<domain>/`
    - Copy `assets/NODE-template.md` to `<brain_path>/tree/<domain>/NODE.md`. Fill placeholders: `{{TITLE}}` = humanized `<domain>`, `{{DOMAIN}}` = `<domain>`, `{{PRIMARY_PROJECT}}` = `project_alias`. Leave `## Leaves` section with the placeholder `*(none yet — use `promote-thread-to-tree` to land the first decision)*`.
7. **Write `thread-index.md`.** Copy `assets/thread-index-template.md` to `<brain_path>/thread-index.md`. Fill `{{PRIMARY_PROJECT}}` and `{{PROJECT_TITLE}}`.
8. **Write `current-state.md`.** Copy `assets/current-state-template.md` to `<brain_path>/current-state.md`. Fill `{{PRIMARY_PROJECT}}` and `{{PROJECT_TITLE}}`.
9. **Place `.gitkeep`** in `<brain_path>/threads/` and `<brain_path>/archive/` so empty directories stay tracked.
10. **Update `~/.config/project-brain/projects.yaml`.** Create the file if it does not exist (with a top-level comment explaining what it is). Append an entry:
    ```yaml
    <project_alias>:
      root: <path to repo root>
      brain: <brain_path>
      remotes:
        - name: <remote-name>
          url: <git remote get-url output>
          default_base: <default_base>
      default_remote: <default_remote>
    ```
    Do not touch other projects' entries.
11. **Write `.gitignore`.** Create `<brain_path>/.gitignore` with entries for `transcript.md` and `attachments/` directories (per CONVENTIONS § 2.5).

12. **Conditional git commit.** If `--init-git` is set, run `git add <brain_path>/ <brain_path>/.gitignore && git commit -m "chore(brain): scaffold project-brain for <project_alias>"`. If `--init-git` is NOT set, the skill DOES NOT commit — the user must run `git commit` themselves. (This defers git to user scope per v1.0.0-rc4 design.)

13. **Update `~/.config/project-brain/projects.yaml`.** Unless `--no-registry` is set, create the file if absent. Append an entry with alias, brain_path, remotes (if available), default_remote (if available). If no remotes, omit that section.

14. **Report.** Return the brain path, the next-step prompt ("You can now run `new-thread` to capture the first thought."), a note about `git commit` if it wasn't run (if `--init-git` was not set), and — if the `$USER@localhost` owner fallback was triggered in step 1 — a one-line reminder: "owner was set to `<$USER>@localhost` (git user.email unset); fix the TODO marker at the top of § 10 in CONVENTIONS.md before committing."

## Side effects

### Files written or modified

| Path (relative to repo root)        | Operation | Notes                                                             |
|-------------------------------------|-----------|-------------------------------------------------------------------|
| `project-brain/`                         | create    | Directory; all subsequent paths live under this.                  |
| `project-brain/CONVENTIONS.md`           | create    | Copied from pack, § 10 spliced with user answers.                 |
| `project-brain/tree/NODE.md`             | create    | Root node; `## Sub-nodes` lists every domain.                     |
| `project-brain/tree/<domain>/NODE.md`    | create    | One per entry in `domain_taxonomy`; empty `## Leaves`.            |
| `project-brain/threads/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `project-brain/archive/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `project-brain/thread-index.md`          | create    | From `assets/thread-index-template.md`.                           |
| `project-brain/current-state.md`         | create    | From `assets/current-state-template.md`.                          |

### User-global files

| Path                        | Operation        | Notes                                                           |
|-----------------------------|------------------|-----------------------------------------------------------------|
| `~/.config/project-brain/projects.yaml`       | create or append | Top-level mapping; one new entry keyed by `project_alias`.      |
| `~/.ai/` (directory)        | create           | Only if missing; mode 0755.                                     |

### Git operations

| Operation                        | Trigger | Notes                                                          |
|----------------------------------|---------|----------------------------------------------------------------|
| `git add project-brain/`              | step 11 | Stages the entire brain scaffold.                              |
| `git commit -m …`                | step 11 | Single bootstrap commit on the current branch (usually main).  |
| `git push <remote> <branch>`     | step 12 | Optional; gated by user confirmation.                          |

### External calls

- **`git init` (if `--init-git` is set)** — only if the directory is not already a git repo. User confirms before running.
- **`git config user.email`** — read-only, to populate the `owner` field.

## Outputs

**User-facing summary.** A short message with:

- The brain path (as a `computer://` link to `project-brain/`).
- The bootstrap commit SHA.
- The list of scaffolded domains, each as a link to its `NODE.md`.
- The `~/.config/project-brain/projects.yaml` path (note that it's user-global, not project-local).
- Push status (pushed / local only).
- A next-step suggestion: "Run `new-thread` to start capturing ideas; run `promote-thread-to-tree` when a thread matures."

**State passed forward.**

- `brain_path` — absolute path to `project-brain/`.
- `bootstrap_commit` — SHA of the scaffolding commit.
- `project_alias` — alias registered in `projects.yaml`.
- `scaffolded_domains` — list of paths like `tree/engineering/NODE.md`.

## Frontmatter flips

This skill only creates files; it does not flip any existing frontmatter. New files are written with their final field values directly — no intermediate states, no subsequent flips within the skill.

## Postconditions

- `<brain_path>/` exists with the directory layout from § 1.
- `<brain_path>/CONVENTIONS.md` is valid — sections 1–9 and 11 match the pack's canonical copy exactly; § 10 is populated from user answers (or explicitly placeholder-marked).
- `<brain_path>/tree/NODE.md` and one `<brain_path>/tree/<domain>/NODE.md` per entry in `domain_taxonomy` exist and have valid frontmatter.
- `<brain_path>/thread-index.md` and `<brain_path>/current-state.md` exist with scaffolded but empty content.
- `~/.config/project-brain/projects.yaml` contains a `project_alias` entry with `brain`, `remotes`, and `default_remote` set.
- A single commit on the current branch contains all brain files.
- All preconditions of `new-thread` and `promote-thread-to-tree` are now satisfied for this project.
- `verify-tree` (if installed) passes on the newly-scaffolded brain.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble.
  - Example output: `Initialized project-brain in ./project-brain/ (alias: my-app, owner: alice@example.com).`
- **normal**: structured summary of what changed (file paths, artifact counts), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Failure modes

| Failure                                | Cause                                                        | Response                                      |
|----------------------------------------|--------------------------------------------------------------|-----------------------------------------------|
| Not in a git repo                      | `git rev-parse --is-inside-work-tree` returns false          | refuse — ask user to `git init` first         |
| Brain path already exists              | `project-brain/` already on disk                                  | refuse — direct to `repair-brain` (not yet drafted) |
| Alias collision in `projects.yaml`     | `project_alias` already registered                           | prompt — suggest `<alias>-2` or new alias     |
| Dirty working tree                     | Uncommitted changes on the current branch                    | refuse — ask user to stash or commit          |
| No remotes and offline not confirmed   | `git remote -v` empty, user did not opt in to offline mode   | refuse — ask user to add a remote or confirm offline |
| Slug validation fails on a domain      | One of `domain_taxonomy` violates § 11.1                     | prompt — re-ask for the offending domain      |
| Pack's `CONVENTIONS.md` not found      | Pack installation broken                                     | refuse — report broken pack                   |
| Write to `~/.config/project-brain/projects.yaml` fails   | Permissions or disk issue                                    | refuse — leave `project-brain/` uncommitted, tell user to fix and re-run |

## Related skills

- **Precedes:** `new-thread` — requires `project-brain/CONVENTIONS.md` and a `projects.yaml` entry, both produced here.
- **Precedes:** `promote-thread-to-tree` — requires the tree scaffold and the `remotes` list from `projects.yaml`.
- **Precedes:** `verify-tree` — the scaffold it produces is the validator's first meaningful input.
- **Compatible with:** `repair-brain` / `migrate-brain` *(not yet drafted)* — what init is not: those handle existing-brain mutations.

## Asset dependencies

- `assets/NODE-template.md` — root + per-domain NODE.md (steps 5, 6).
- `assets/thread-index-template.md` — initial `thread-index.md` (step 7).
- `assets/current-state-template.md` — initial `current-state.md` (step 8).
- `pack/CONVENTIONS.md` — the canonical conventions doc, read at step 4 and spliced with § 10 answers.

## Versioning

**0.1.0** — initial draft. Major bump if the bootstrap-commit shape changes (e.g. split into multiple commits), if pre-scaffolded domain directories become optional, or if the `projects.yaml` schema moves elsewhere.
