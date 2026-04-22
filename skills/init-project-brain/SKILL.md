---
name: init-project-brain
description: One-time scaffold of the project-brain skeleton into a git repo. Creates thoughts/ with CONVENTIONS.md (section 10 filled from user answers), tree/NODE.md root and one NODE.md per top-level domain from section 10.1, empty threads/ and archive/, plus thread-index.md and current-state.md scaffolds. Appends the project alias entry with remotes and default_remote to ~/.ai/projects.yaml (creating the file if absent), then commits on main and optionally pushes. Use when the user says "set up project brain", "install project-brain here", "init the brain", or adopts this pack in a new repo for the first time.
version: 0.1.0
pack: project-brain
requires:
  - git
  - "read:pack/CONVENTIONS.md"
  - "write:[project-root]"
  - "write:~/.ai/projects.yaml"
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
| `project_alias`     | user prompt                     | yes      | Kebab-case key for `~/.ai/projects.yaml` (§ 11.1). Must not already exist in the registry. |
| `project_title`     | user prompt                     | yes      | Human-readable name used in `thread-index.md` and `current-state.md` headers.             |
| `brain_path`        | user prompt (default = cwd)     | yes      | Absolute path where `thoughts/` is to live. Defaults to `<cwd>/thoughts`.                 |
| `remotes`           | `git remote -v` + user prompt   | yes      | List of remotes the brain repo may push to. Detected from git; user confirms each entry.  |
| `default_remote`    | user prompt                     | conditional | Required when `remotes` has >1 entry; defaults to the sole entry otherwise.            |
| `default_base_per_remote` | user prompt               | yes      | Per-remote default base branch (usually `main` or `master`). One value per remote.        |
| `domain_taxonomy`   | user prompt                     | yes      | § 10.1 top-level domains as a line-separated list (e.g. `engineering / product / operations`). 1–8 entries. |
| `debate_personas`   | user prompt                     | no       | § 10.2 reviewer personas. Default empty — easy to add later by hand-editing `CONVENTIONS.md`. |
| `build_toolchain`   | user prompt                     | no       | § 10.3 test/lint/build commands. Default empty.                                           |
| `owner`             | `git config user.email`         | yes      | Who ran init; recorded in the bootstrap commit.                                           |

Prompt strategy: one `AskUserQuestion` call collects `project_alias` + `project_title` + `brain_path` + `domain_taxonomy`. A second call confirms the detected remotes and asks for `default_base` per remote. `debate_personas` and `build_toolchain` are asked separately and can be skipped.

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a git repository (`git rev-parse --is-inside-work-tree` returns `true`).
2. The target `brain_path` does not already exist. If it does, refuse — direct the user at a hypothetical `repair-brain` or ask them to move the existing directory first.
3. Working tree is clean on `main` (or the project's default branch). Init commits directly to that branch; uncommitted changes would be swept into the bootstrap commit.
4. `git config user.email` returns a value.
5. `~/.ai/projects.yaml`, if it exists, does **not** already contain `project_alias`. If it does, prompt — suggest a suffixed alias (`<alias>-2`) or ask the user to pick a different one.
6. `git remote -v` returns at least one remote, OR the user explicitly confirms offline-only scaffolding (no push, no remote entry in `projects.yaml`).
7. Each entry in `domain_taxonomy` matches the slug rules of § 11.1 (kebab-case, no sub-paths — sub-nesting emerges through promotion, not init).

## Process

Each step is atomic. A failure at step N leaves the filesystem in whatever state it was after step N-1; no partial scaffolds are left committed.

1. **Resolve inputs.** Prompt for `project_alias`, `project_title`, `brain_path`, `domain_taxonomy`. Detect remotes via `git remote -v` and present them for confirmation; collect `default_base` per remote. Read `git config user.email` for `owner`. Optional second pass: `debate_personas` and `build_toolchain`.
2. **Validate preconditions.** Run checks 1–7. On failure, stop and report the specific precondition.
3. **Create brain directory.** `mkdir -p <brain_path>/tree <brain_path>/threads <brain_path>/archive`.
4. **Write `CONVENTIONS.md`.** Read the pack's canonical `CONVENTIONS.md` (the one this pack ships). Splice § 10 subsections with the user's answers:
    - § 10.1 Tree domain taxonomy — replaced with the `domain_taxonomy` list as a fenced-block outline.
    - § 10.2 Debate personas — replaced with `debate_personas` if provided; otherwise keep the placeholder with a "— TBD; add personas before invoking `multi-agent-debate`" comment.
    - § 10.3 Build toolchain — replaced with `build_toolchain` if provided; otherwise leave as commented placeholders.
    - § 10.4 — untouched unless `role_extensions` was volunteered (rare at init time).
   Write to `<brain_path>/CONVENTIONS.md`. Do not modify the sections above § 10 — those are the pack's shared contract.
5. **Scaffold the root NODE.md.** Copy `assets/NODE-template.md` to `<brain_path>/tree/NODE.md`. Fill placeholders: `{{TITLE}}` = `"<project_title> — Knowledge Tree"`, `{{DOMAIN}}` = `/`, `{{PRIMARY_PROJECT}}` = `project_alias`. Populate the `## Sub-nodes` section with one bullet per entry in `domain_taxonomy`, each linked to the sub-directory's `NODE.md`.
6. **Scaffold per-domain NODE.md.** For each `<domain>` in `domain_taxonomy`:
    - `mkdir -p <brain_path>/tree/<domain>/`
    - Copy `assets/NODE-template.md` to `<brain_path>/tree/<domain>/NODE.md`. Fill placeholders: `{{TITLE}}` = humanized `<domain>`, `{{DOMAIN}}` = `<domain>`, `{{PRIMARY_PROJECT}}` = `project_alias`. Leave `## Leaves` section with the placeholder `*(none yet — use `promote-thread-to-tree` to land the first decision)*`.
7. **Write `thread-index.md`.** Copy `assets/thread-index-template.md` to `<brain_path>/thread-index.md`. Fill `{{PRIMARY_PROJECT}}` and `{{PROJECT_TITLE}}`.
8. **Write `current-state.md`.** Copy `assets/current-state-template.md` to `<brain_path>/current-state.md`. Fill `{{PRIMARY_PROJECT}}` and `{{PROJECT_TITLE}}`.
9. **Place `.gitkeep`** in `<brain_path>/threads/` and `<brain_path>/archive/` so empty directories stay tracked.
10. **Update `~/.ai/projects.yaml`.** Create the file if it does not exist (with a top-level comment explaining what it is). Append an entry:
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
11. **Commit on main.** `git add <brain_path>/ && git commit -m "chore(brain): scaffold project-brain for <project_alias>"`. The `~/.ai/projects.yaml` update is a user-global file and is not part of this commit. Report the SHA.
12. **Optional push.** Ask the user via `AskUserQuestion` whether to push the commit now. If yes, `git push <default_remote> <current-branch>`. If no, report that the commit is local and can be pushed manually.
13. **Report.** Return the brain path, the bootstrap commit SHA, the list of scaffolded domains, the `projects.yaml` path, and a next-step prompt: "You can now run `new-thread` to capture the first thought."

## Side effects

### Files written or modified

| Path (relative to repo root)        | Operation | Notes                                                             |
|-------------------------------------|-----------|-------------------------------------------------------------------|
| `thoughts/`                         | create    | Directory; all subsequent paths live under this.                  |
| `thoughts/CONVENTIONS.md`           | create    | Copied from pack, § 10 spliced with user answers.                 |
| `thoughts/tree/NODE.md`             | create    | Root node; `## Sub-nodes` lists every domain.                     |
| `thoughts/tree/<domain>/NODE.md`    | create    | One per entry in `domain_taxonomy`; empty `## Leaves`.            |
| `thoughts/threads/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `thoughts/archive/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `thoughts/thread-index.md`          | create    | From `assets/thread-index-template.md`.                           |
| `thoughts/current-state.md`         | create    | From `assets/current-state-template.md`.                          |

### User-global files

| Path                        | Operation        | Notes                                                           |
|-----------------------------|------------------|-----------------------------------------------------------------|
| `~/.ai/projects.yaml`       | create or append | Top-level mapping; one new entry keyed by `project_alias`.      |
| `~/.ai/` (directory)        | create           | Only if missing; mode 0755.                                     |

### Git operations

| Operation                        | Trigger | Notes                                                          |
|----------------------------------|---------|----------------------------------------------------------------|
| `git add thoughts/`              | step 11 | Stages the entire brain scaffold.                              |
| `git commit -m …`                | step 11 | Single bootstrap commit on the current branch (usually main).  |
| `git push <remote> <branch>`     | step 12 | Optional; gated by user confirmation.                          |

### External calls

None. Purely local filesystem + git.

## Outputs

**User-facing summary.** A short message with:

- The brain path (as a `computer://` link to `thoughts/`).
- The bootstrap commit SHA.
- The list of scaffolded domains, each as a link to its `NODE.md`.
- The `~/.ai/projects.yaml` path (note that it's user-global, not project-local).
- Push status (pushed / local only).
- A next-step suggestion: "Run `new-thread` to start capturing ideas; run `promote-thread-to-tree` when a thread matures."

**State passed forward.**

- `brain_path` — absolute path to `thoughts/`.
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
- `~/.ai/projects.yaml` contains a `project_alias` entry with `brain`, `remotes`, and `default_remote` set.
- A single commit on the current branch contains all brain files.
- All preconditions of `new-thread` and `promote-thread-to-tree` are now satisfied for this project.
- `verify-tree` (if installed) passes on the newly-scaffolded brain.

## Failure modes

| Failure                                | Cause                                                        | Response                                      |
|----------------------------------------|--------------------------------------------------------------|-----------------------------------------------|
| Not in a git repo                      | `git rev-parse --is-inside-work-tree` returns false          | refuse — ask user to `git init` first         |
| Brain path already exists              | `thoughts/` already on disk                                  | refuse — direct to `repair-brain` (not yet drafted) |
| Alias collision in `projects.yaml`     | `project_alias` already registered                           | prompt — suggest `<alias>-2` or new alias     |
| Dirty working tree                     | Uncommitted changes on the current branch                    | refuse — ask user to stash or commit          |
| No remotes and offline not confirmed   | `git remote -v` empty, user did not opt in to offline mode   | refuse — ask user to add a remote or confirm offline |
| Slug validation fails on a domain      | One of `domain_taxonomy` violates § 11.1                     | prompt — re-ask for the offending domain      |
| Pack's `CONVENTIONS.md` not found      | Pack installation broken                                     | refuse — report broken pack                   |
| Write to `~/.ai/projects.yaml` fails   | Permissions or disk issue                                    | refuse — leave `thoughts/` uncommitted, tell user to fix and re-run |

## Related skills

- **Precedes:** `new-thread` — requires `thoughts/CONVENTIONS.md` and a `projects.yaml` entry, both produced here.
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
