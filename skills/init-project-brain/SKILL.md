---
name: init-project-brain
description: One-time scaffold of the project-brain skeleton into the host environment's project directory. Default invocation runs with **zero interactive questions in the common case** — the skill detects the host project root (Cowork workspace folder, Codex project root, Claude Code cwd, or the nearest git repo root) and scaffolds `project-brain/` inside it. A confirmation is printed showing which source the root came from. The skill only prompts if detection falls all the way through to raw cwd with no git signal, OR if an existing brain is already scaffolded at the target (overwrite vs cancel). Alias and title are derived from the detected home's last-path-component. Owner is written as the literal placeholder `TODO@example.com` with a TODO marker in CONVENTIONS.md § 10 — the user replaces it on their first commit, or leaves it until promote-time. If an existing `project-brain/` is already scaffolded, the skill prompts "overwrite (backup and replace) or cancel?" — it never silently clobbers. Creates project-brain/ with CONVENTIONS.md, config.yaml, tree/NODE.md, empty threads/ and archive/, plus a .gitignore for transcripts and attachments. Optional --home=<path> skips detection. Optional --force skips the overwrite prompt. Optional --interactive prompts for all values (owner, domains, etc.). Optional --owner <email> sets owner explicitly without the TODO marker. Optional --init-git runs git init + scaffold commit (opts into git-based preconditions). Optional --no-registry skips appending an alias entry to ~/.config/project-brain/projects.yaml. Use when the user says "set up project brain", "install project-brain here", or adopts this pack in a new directory first time.
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:pack/CONVENTIONS.md"
  - "write:[project-root]"
  - "write:~/.config/project-brain/projects.yaml"
# Note: `git` was listed as a hard requirement pre-rc4. rc4 makes it optional —
# git is only invoked when --init-git is passed. The default flow is a plain
# `mkdir` + file-write, no git at all.
---

# init-project-brain

Turns any directory into a project-brain-enabled one. Before this skill runs, there is no place for threads to live and no tree structure for decisions to land in; after it runs, every other skill in the pack has its preconditions met. This is the first skill a user invokes when adopting the pack in a new project.

**Host-project detection (rc4):** the skill commits to a 1:1 correspondence between a project-brain project and the host environment's project concept — Cowork workspace folder, Codex project root, Claude Code cwd, or the nearest git repo root (see CONVENTIONS § 1). It calls `scripts/verify_tree/config.py::detect_host_project_root()` (pure Python — env-var probes + file-existence walk, zero shell invocation) and uses the detected path as the project home.

The detection chain, highest priority first:

1. `PROJECT_BRAIN_HOME` env override — for scripts / CI.
2. `COWORK_WORKSPACE_FOLDER` — Cowork sets this at session start.
3. `CODEX_PROJECT_ROOT` — Codex equivalent.
4. `CLAUDE_PROJECT_ROOT` — Claude Code equivalent.
5. Nearest ancestor of cwd containing `.git/` — almost all real projects hit this.
6. Raw cwd — last-resort fallback (bare directory, no git).

**Default flow: zero prompts** if detection returns any source 1–5. The skill prints a single confirmation line (`Project home: /path (detected: cowork-workspace)`) and proceeds. Users who want a different location pass `--home=<path>` to override. Users can see which source was chosen in the output to confirm it matches their expectation.

**Fallback flow: one prompt** if detection lands on source 6 (raw cwd with no git). The ambiguity is real — the agent has no idea where the project should live — so one AskUserQuestion surfaces with cwd as the default and the user can accept or type an alternative.

**Existing-brain detection:** if a `project-brain/` directory already exists at the chosen location and contains a `CONVENTIONS.md`, the skill stops and asks: **"A brain already exists at `<path>`. Overwrite (rename existing to `project-brain.bak.<timestamp>/` and scaffold fresh), or cancel?"** Default is cancel. The skill never silently clobbers existing work; the backup-rename is recoverable so mistakes cost nothing.

**Git is optional (rc4).** The default flow is a plain directory scaffold — no `git init`, no commit, no repo required. Pass `--init-git` if you want init to run `git init` and commit the scaffold. Users who already have a git repo and just want the brain scaffolded without an auto-commit run the skill without any flag; they can `git add && git commit` themselves when ready.

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
| `project_home`      | **detected** via `detect_host_project_root()` (see preamble); falls through to one AskUserQuestion only when detection returns the raw-cwd source | yes | Absolute path to the directory the brain will live **inside** (i.e., parent of `project-brain/`). Detection chain consults env vars (`PROJECT_BRAIN_HOME`, `COWORK_WORKSPACE_FOLDER`, `CODEX_PROJECT_ROOT`, `CLAUDE_PROJECT_ROOT`), then walks for `.git/`, then cwd. Override with `--home=<path>`. |
| `brain_path`        | derived from `project_home`     | yes      | Computed as `<project_home>/project-brain`. |
| `remotes`           | **`--init-git` only** — `git remote -v` + user prompt | conditional | List of remotes the brain repo may push to. Only collected when `--init-git` is passed. In the default flow the registry entry (if written at all) omits the `remotes:` block and promote-time fills it in. |
| `default_remote`    | **`--init-git` only** — user prompt | conditional | Required when `remotes` has >1 entry; defaults to the sole entry otherwise. Default flow skips. |
| `default_base_per_remote` | **`--init-git` only** — user prompt | conditional | Per-remote default base branch (usually `main` or `master`). Default flow skips.   |
| `domain_taxonomy`   | user prompt                     | yes      | § 10.1 top-level domains as a line-separated list (e.g. `engineering / product / operations`). 1–8 entries. |
| `debate_personas`   | user prompt                     | no       | § 10.2 reviewer personas. Default empty — easy to add later by hand-editing `CONVENTIONS.md`. |
| `build_toolchain`   | user prompt                     | no       | § 10.3 test/lint/build commands. Default empty.                                           |
| `owner`             | `--owner <email>` flag, else the literal placeholder `TODO@example.com` (with a visible TODO marker in CONVENTIONS § 10). If `--init-git` is set, `$EMAIL` and `git config user.email` are also consulted as intermediate fallbacks. **No shell invocation in the default flow.** | yes      | Who ran init; recorded as thread owner, registry entry, etc.                              |

**Zero-Q&A defaults (new in v1.0.0-rc4):**
- `project_home`: **detected**, not asked. Resolution chain: `--home=<path>` flag > `PROJECT_BRAIN_HOME` env > `COWORK_WORKSPACE_FOLDER` > `CODEX_PROJECT_ROOT` > `CLAUDE_PROJECT_ROOT` > nearest `.git/` ancestor > raw cwd. The skill calls `scripts/verify_tree/config.py::detect_host_project_root()` which is pure Python (env reads + file-existence walk, no shell). The *only* case that triggers an interactive prompt is the raw-cwd fallback (source = `cwd`) — everywhere else the skill prints a confirmation line and proceeds.
- `project_alias`: kebab-case slug of the chosen `project_home`'s last-path-component (e.g., `/Users/alice/workspace/My App` → `my-app`). **Derive this from the chosen-path string in memory — do NOT run `basename`, `pwd`, or any shell command to discover it.** Validated per § 11.1.
- `project_title`: title-cased form of the same last-path-component (e.g., `my-app` → `My App`). Same no-shell rule.
- `owner` (default flow): the **literal placeholder string `TODO@example.com`**. A visible TODO marker is prepended to CONVENTIONS.md § 10 naming what needs to change (see Process step 4). **The default flow does NOT invoke `git`, does NOT read `$EMAIL`, does NOT read `$USER`, does NOT run any shell command to guess who the user is.** The user fixes the placeholder when they feel like it — at first commit, or at first promote (where a real identity is needed anyway and the promote-time heads-up will remind them). Rationale: even reading env vars requires a `bash` invocation in agentic IDEs, which triggers a permission prompt. The user's mental model for install is "setup → Done, no questions, no prompts." We honor that by not trying to be smart about identity.
- `owner` (with `--owner <email>`): use the supplied email verbatim. No TODO marker in § 10.
- `owner` (with `--init-git`): `$EMAIL` → `git config user.email` → `TODO@example.com` TODO fallback. Env var and git consultation are OK here because `--init-git` is already invoking the shell and git for `init` + `commit`.
- `domain_taxonomy`: `engineering`. A single default domain. User adds more by hand-editing CONVENTIONS.md § 10.1 or re-runs with `--interactive`.

**Prompt strategy:** Default invocation asks zero interactive questions AND runs zero shell commands. With `--interactive` flag, one call collects `project_alias` + `project_title` + `owner` + `domain_taxonomy`. Remote/base confirmation and persona/toolchain setup happen only with `--interactive`.

## Preconditions

The skill **refuses** if any of these are not met. Preconditions 1, 3, 6 apply **only when `--init-git` is set** — rc4 makes git entirely optional and the default install creates a plain directory with no git involvement.

1. (Only if `--init-git`) Current working directory is inside a git repository (`git rev-parse --is-inside-work-tree` returns `true`). Without `--init-git` the skill does not care — the brain is just a directory full of markdown.
2. The target `brain_path` does not already contain a brain (`<brain_path>/CONVENTIONS.md` doesn't exist). **Handling:**
    - If `brain_path` does not exist at all: proceed silently.
    - If `brain_path` exists but is empty or has no `CONVENTIONS.md`: proceed silently (treating as a partial / abandoned scaffold).
    - If `brain_path/CONVENTIONS.md` exists: prompt via AskUserQuestion: `"A project-brain already exists at <brain_path>. Overwrite (rename existing to project-brain.bak.<YYYYMMDD-HHMMSS>/ and scaffold fresh) or cancel?"` — default is **cancel**. If the user picks overwrite, rename the existing directory to `<brain_path>.bak.<timestamp>` (with seconds precision to avoid collisions on rapid re-invocation) and continue. If the user picks cancel, exit cleanly with a one-line report (`Brain already exists at <path>; no changes made.`). Skip this prompt if `--force` is set (auto-overwrite) or abort immediately if neither flag is set and the prompt can't be shown.
3. (Only if `--init-git`) Working tree is clean on `main` (or the project's default branch). Init's `--init-git` commits directly to that branch; uncommitted changes would be swept into the bootstrap commit.
4. The `owner` field is seeded from the `--owner <email>` flag if given. Otherwise it's written as the literal placeholder `TODO@example.com` and a visible TODO marker is prepended to CONVENTIONS.md § 10 (see Process step 4). **The default flow does NOT invoke any shell command to guess the user's identity** — no `git config`, no `echo $EMAIL`, no `whoami`. Every shell invocation in agentic IDEs triggers a permission prompt, and the user's mental model for init is "setup → Done, no questions." Only when `--init-git` is set does the skill optionally consult `$EMAIL` then `git config user.email` as fallbacks — that path is already invoking the shell and git for `init` + `commit`, so one more read is no additional friction. This precondition is always best-effort — it never refuses.
5. `~/.config/project-brain/projects.yaml`, if it exists, does **not** already contain `project_alias`. If it does, prompt — suggest a suffixed alias (`<alias>-2`) or ask the user to pick a different one. (Skipped entirely if `--no-registry` is set.)
6. (Only if `--init-git` AND the user wants a registry entry with remote info) `git remote -v` returns at least one remote, OR the user explicitly confirms offline-only scaffolding. Without `--init-git`, the registry entry omits the `remotes:` block regardless.
7. Each entry in `domain_taxonomy` matches the slug rules of § 11.1 (kebab-case, no sub-paths — sub-nesting emerges through promotion, not init).

## Process

> ### ⛔️ HARD CONSTRAINT FOR THE AGENT
>
> **All mechanical scaffolding happens inside `${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh` — a single Bash tool call.** You, the agent, **MUST NOT**:
>
> - Read template files yourself (`Read assets/...`, `Glob assets/...`). The script reads them.
> - Write scaffold files yourself (`Write project-brain/CONVENTIONS.md`, `Write project-brain/config.yaml`, etc.). The script writes them.
> - Run `mkdir` or `mv` yourself as separate Bash calls. The script does `mkdir`, and the script handles backup-rename under `--force`.
> - Create `tree/engineering/` or any other domain subdirectory. Tree stays flat at init. Domain dirs appear on demand when `promote-thread-to-tree` lands the first decision there.
> - "Write all the scaffold files in parallel." No. Call the script, nothing else.
>
> **You MUST call `${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh` exactly once, with appropriate flags, and nothing else in the mechanical-scaffolding path.** `CLAUDE_PLUGIN_ROOT` is the env var Claude Code exports for plugin skills; it resolves to this pack's install root. **Do not** strip it off and call `scripts/init-brain.sh` bare — the relative path would resolve against the skill's own directory and fail. Every departure from this cascades into a 6-minute session of individual permission prompts. The script completes in under 100ms.
>
> If you find yourself typing any of: `Read assets/`, `Write .../project-brain/`, `mkdir .../project-brain/`, `mv .../project-brain project-brain.bak` — STOP. You are improvising. The single correct Bash call is in Step 3 below.

Steps in order:

1. **Resolve inputs (pre-script, no file ops).** init-brain.sh handles host-project detection internally in pure bash — the same priority chain `detect_host_project_root()` uses (`PROJECT_BRAIN_HOME` → `COWORK_WORKSPACE_FOLDER` → `CODEX_PROJECT_ROOT` → `CLAUDE_PROJECT_ROOT` → nearest `.git/` ancestor → cwd). It also derives `alias`/`title` from the detected home's basename when they aren't supplied. **Don't invoke any Python helper yourself** — just omit `--home`, `--alias`, `--title` and let the script do it. The only manual resolution is `owner`: if the caller passed `--owner=<email>`, forward it; otherwise omit the flag and the script writes the literal placeholder `TODO@example.com`. **Do NOT invoke `git config user.email`, do NOT read `$EMAIL` or `$USER`, do NOT run any shell command to guess.** rc4 default flow is 100% shell-free except for the single script call in Step 3.

2. **Detect existing brain (read-only file test, no shell).** Use the Read tool (or equivalent) to check whether `<project_home>/project-brain/CONVENTIONS.md` exists.
    - Absent: proceed to Step 3 with no `--force` flag.
    - Present: present an AskUserQuestion: `"A project-brain is already scaffolded at <brain_path>. Overwrite (backup to project-brain.bak.<timestamp>/ and scaffold fresh) or cancel?"` Default = cancel. On "overwrite", proceed to Step 3 WITH `--force` (the script handles the backup-rename internally — **do not `mv` yourself**). On "cancel", exit cleanly with a one-liner.

3. **Call the scaffolding script. This is the ONLY mechanical tool call.**

   Bash tool call (one invocation, one permission prompt):

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh" \
     [--home='<project_home>'] \   # optional; script auto-detects from env + .git walk
     [--alias='<alias>']       \   # optional; derived from home basename
     [--title='<title>']       \   # optional; derived from home basename
     [--owner='<email>']       \   # only if --owner was passed to the skill
     [--with-registry]         \   # only if --no-registry was NOT passed
     [--force]                 \   # only if Step 2's prompt returned "overwrite"
     [--init-git]                  # only if --init-git was passed to the skill
   ```

   **In most cases no flags are needed at all.** The script detects the host project, derives alias/title from its basename, and scaffolds. Pass flags only when the user has overridden something explicitly. The success line prints the detected home + source so the user can sanity-check (`project home auto-detected via cowork-workspace.`).

   **Do not call any other tool before this bash call** except the AskUserQuestion and file-existence check described in Steps 1–2. In particular: do not Read template files "to understand what the script will write" — the script is self-contained and tested.

   What the script does internally (for your understanding only — you don't replicate this; the script does it):

   - Creates `project-brain/{tree,threads,archive}` with `.gitkeep` in each, nothing else. Tree stays flat. No domain subdirectory.
   - Copies `<pack>/CONVENTIONS.md` verbatim, prepends TODO marker to § 10 if owner is the placeholder.
   - Copies + substitutes `thread-index.md` and `current-state.md` templates.
   - Writes `config.yaml` + `.gitignore` from scratch (small fixed content).
   - Optionally registers in `~/.config/project-brain/projects.yaml` under `--with-registry`.
   - Optionally runs `git init` + single commit under `--init-git`. Default is git-free.
   - Prints a terse one-liner to stdout + optional placeholder hint.

4. **Report.** Passthrough the script's stdout verbatim and prepend one detection line. Do not add any of your own commentary. At verbosity=terse the full user-visible output is exactly:

    ```
    Project home: <project_home>  (source: <detection_source>)
    Initialized project-brain in <project_home>/project-brain/ (alias: <alias>, owner: <owner>).
      owner = TODO@example.com placeholder; replace in CONVENTIONS § 10 when ready.     # only if placeholder was used
    ```

    Do not mention git, commits, or "run git add". Capture is git-free; promote-time is where git shows up. Telling the user about git at init cues a mental model this pack has intentionally moved away from.

    At verbosity=normal or verbose, expand with file list / registry entry / next-step suggestions as before.

## Side effects

### Files written or modified

| Path (relative to repo root)        | Operation | Notes                                                             |
|-------------------------------------|-----------|-------------------------------------------------------------------|
| `project-brain/`                         | create    | Directory; all subsequent paths live under this.                  |
| `project-brain/CONVENTIONS.md`           | create    | Copied from pack, § 10 spliced with user answers. TODO marker prepended if the `TODO@example.com` owner placeholder was used (default flow without `--owner`). |
| `project-brain/config.yaml`              | create    | rc4 per-project config with `primary_project`, default `verbosity: terse`, `transcript_logging: on`, empty `aliases: {}`. |
| `project-brain/.gitignore`               | create    | Defaults for `transcript.md` + `attachments/` per CONVENTIONS § 2.5. |
| `project-brain/tree/NODE.md`             | create    | Root node; `## Sub-nodes` lists every domain.                     |
| `project-brain/tree/<domain>/NODE.md`    | create    | One per entry in `domain_taxonomy`; empty `## Leaves`.            |
| `project-brain/threads/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `project-brain/archive/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `project-brain/thread-index.md`          | create    | From `assets/thread-index-template.md`.                           |
| `project-brain/current-state.md`         | create    | From `assets/current-state-template.md`.                          |

### User-global files

| Path                        | Operation        | Notes                                                           |
|-----------------------------|------------------|-----------------------------------------------------------------|
| `~/.config/project-brain/projects.yaml`       | create or append | Top-level mapping; one new entry keyed by `project_alias`. Skipped entirely when `--no-registry` is set. |
| `~/.config/project-brain/` (directory)        | create           | Only if missing; mode 0755. Skipped when `--no-registry` is set. |

### Git operations

**Default flow (no `--init-git`): zero git operations.** Listed below for the `--init-git` flow only.

| Operation                        | Trigger                               | Notes                                                          |
|----------------------------------|---------------------------------------|----------------------------------------------------------------|
| `git init`                       | `--init-git` + not-yet-a-git-repo     | Creates a fresh git repo in the project root.                  |
| `git add project-brain/`         | `--init-git`, Process step 12         | Stages the entire brain scaffold + its `.gitignore`.           |
| `git commit -m …`                | `--init-git`, Process step 12         | Single bootstrap commit on the current branch (usually main).  |
| `git push <remote> <branch>`     | *never automatic* — user runs manually | The skill does not push. Users push themselves when ready.    |

### External calls

Default flow (no `--init-git`): **truly zero external calls.** The skill does `mkdir` + `read/write` of markdown/yaml files via the file tool. No shell invocation of any kind — no `git`, no `gh`, no `basename`, no `pwd`, no `echo $EMAIL`, no `whoami`, no network. The cwd string comes from the agent's invocation context (already known without calling `pwd`); the owner is a literal placeholder. This is what "setup → Done, no questions" means at the tool-call level.

With `--init-git`:

- **`git init`** — only if the directory is not already a git repo. User confirms before running.
- **`echo $EMAIL`** — env-var read, consulted as a fallback owner source between `--owner <email>` and `git config user.email`.
- **`git config user.email`** — read-only, consulted as a fallback owner source between `$EMAIL` and the `TODO@example.com` placeholder.
- **`git add` + `git commit`** — bootstrap commit of the scaffolded brain.
- **`git remote -v`** (optional) — consulted when the registry entry should record remotes.

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
| Brain already scaffolded at target     | `<brain_path>/CONVENTIONS.md` exists                        | prompt via AskUserQuestion — `overwrite` renames existing to `.bak.<timestamp>/` and proceeds; `cancel` (default) exits cleanly. `--force` skips the prompt and overwrites. `--force` + already-scaffolded always overwrites. |
| Empty `<brain_path>` directory exists  | `<brain_path>/` exists but has no `CONVENTIONS.md`          | proceed silently, treating as an abandoned partial scaffold. Files in the existing dir are overwritten by the fresh scaffold; pre-existing unrelated files are preserved. |
| Alias collision in `projects.yaml`     | `project_alias` already registered                           | prompt — suggest `<alias>-2` or new alias (or pass `--no-registry` to skip the registry step) |
| Invalid domain slug                    | One of `domain_taxonomy` fails § 11.1                        | refuse — name the offending slug and the rule it violated |
| Not in a git repo *(only with `--init-git`)* | `git rev-parse --is-inside-work-tree` returns false    | refuse — ask user to `git init` first, or drop the `--init-git` flag to scaffold a plain directory |
| Dirty working tree *(only with `--init-git`)* | Uncommitted changes on the current branch             | refuse — ask user to stash or commit, or drop `--init-git` |
| No remotes and offline not confirmed *(only with `--init-git`)* | `git remote -v` empty, user did not opt in to offline mode | refuse — ask user to add a remote, confirm offline, or drop `--init-git` |
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
