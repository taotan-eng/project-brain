# Installing the `project-brain` skill pack

This file is the **authoritative install procedure** for the pack. The steps below are numbered and deterministic so that either a human or an AI agent can follow them unambiguously. If anything in the top-level `README.md` appears to disagree with this file, **this file wins**.

## Prerequisites

The pack assumes all of the following are available on the install target:

- `git` 2.30+
- `bash` (macOS ships 3.2; tested with 4+ on Linux — either works)
- `python3` 3.10+ (used by `scripts/verify-tree.py`; optional if you replace it with an equivalent)
- `gh` CLI 2.0+, authenticated against the project's remote (required only for the promote / finalize / discard-promotion trio)
- A POSIX filesystem (Windows users: install under WSL)

The pack does **not** require Node, Docker, or any language-specific package manager. The scripts in `scripts/` are pure Python.

## One-time global setup (idempotent)

```sh
# Ensure the user-global registry file exists. All skills that resolve project
# aliases read this file; init-project-brain appends to it.
mkdir -p ~/.ai
[ -f ~/.ai/projects.yaml ] || echo "# project-brain registry" > ~/.ai/projects.yaml
```

## Install procedure

### Step 1 — Obtain the pack

```sh
# Pick a scratch location. Anywhere outside the project you're installing into.
PACK_SRC="/tmp/project-brain-pack"
rm -rf "$PACK_SRC"
git clone <repo-url> "$PACK_SRC"
```

Replace `<repo-url>` with the pack's GitHub URL.

### Step 2 — Place the skills where your runtime will find them

The pack ships as `skills/`, `assets/`, `scripts/`, and `CONVENTIONS.md`. Where these go depends on which agent runtime you are installing into. Pick **exactly one** of the following layouts:

#### 2a. Claude Code layout (recommended for Claude Code users)

```sh
cd <your-project-root>
mkdir -p .claude/skills
cp -R "$PACK_SRC/skills/"*   .claude/skills/
# CONVENTIONS.md and supporting assets/scripts land alongside the future brain:
mkdir -p thoughts
cp    "$PACK_SRC/CONVENTIONS.md" thoughts/CONVENTIONS.md
cp -R "$PACK_SRC/assets"         thoughts/.pack-assets
cp -R "$PACK_SRC/scripts"        thoughts/.pack-scripts
```

Verify:

```sh
ls .claude/skills/
# Expected output (alphabetical):
#   discard-promotion  discard-thread  finalize-promotion  init-project-brain
#   materialize-context  multi-agent-debate  new-thread  park-thread
#   promote-thread-to-tree  update-thread  verify-tree
```

#### 2b. Generic / other-runtime layout

If your runtime does not have a well-known "skill pack" directory, use a neutral location inside the project and treat every SKILL.md as a prompt-able instruction sheet:

```sh
cd <your-project-root>
mkdir -p thoughts
cp    "$PACK_SRC/CONVENTIONS.md" thoughts/CONVENTIONS.md
cp -R "$PACK_SRC/skills"         thoughts/.pack-skills
cp -R "$PACK_SRC/assets"         thoughts/.pack-assets
cp -R "$PACK_SRC/scripts"        thoughts/.pack-scripts
```

To "invoke" a skill in this layout, open `thoughts/.pack-skills/<skill-name>/SKILL.md` in your agent and ask it to follow the Process section.

### Step 3 — Run `init-project-brain`

This is the only skill that runs before the brain is scaffolded; every other skill refuses until `thoughts/CONVENTIONS.md` exists. You ran step 2 which puts CONVENTIONS.md in place, so init can now complete the rest of the scaffold.

#### 3a. Claude Code

Ask Claude Code:

> Run the `init-project-brain` skill. I'll answer the prompts.

Or invoke it directly if your session supports slash-style skill invocation.

#### 3b. Any other runtime

Open `skills/init-project-brain/SKILL.md` (or the `.pack-skills/` variant) in your agent and paste this prompt:

> Follow the Process section of this SKILL.md exactly. Ask me the inputs listed in the Inputs table one by one. Honor the Preconditions and Postconditions. Commit once, as specified.

### Step 4 — Verify the install

```sh
cd <your-project-root>/thoughts

# If you have Python and the scripts installed:
python3 .pack-scripts/verify-tree.py
# Expected: exit 0, prints "PASS".

# Confirm the project alias registered:
grep -A5 "^$(basename $(cd .. && pwd)):" ~/.ai/projects.yaml
# (Or grep for whatever alias you chose during init — it's case-sensitive.)
```

The install is complete when:

1. `thoughts/` exists at the project root.
2. `thoughts/CONVENTIONS.md` is present and its version frontmatter matches the pack's current version.
3. `thoughts/tree/NODE.md` exists, plus one `NODE.md` per top-level domain you configured.
4. `thoughts/thread-index.md` and `thoughts/current-state.md` exist.
5. `~/.ai/projects.yaml` contains your new project's entry with a `brain:` path pointing at `thoughts/` and a `remotes:` list with at least one entry.
6. The bootstrap commit is on your current branch (not pushed unless you asked `init` to push).
7. `verify-tree` exits 0.

## Upgrading a prior install

This pack is pre-1.0; upgrades may require manual migration. The rule of thumb:

1. Read `CONVENTIONS.md` Appendix A for every version between your current and target.
2. Apply schema additions (new optional frontmatter fields) by running `verify-tree` — most will pass through unchanged since the new fields are optional.
3. For required-field additions or layout changes, the changelog entry lists the migration steps. If there is no migration note, no migration is needed.

If an upgrade breaks `verify-tree`, revert `CONVENTIONS.md` to your previous version, commit, open an issue against the pack describing the break, and hold until a `repair-brain` skill lands (currently deferred).

## Uninstall

The pack has no runtime state outside `thoughts/` and `~/.ai/projects.yaml`. To uninstall:

```sh
cd <your-project-root>
# Remove the brain:
rm -rf thoughts/
# If installed at Claude Code layout, also:
rm -rf .claude/skills/{init-project-brain,new-thread,update-thread,park-thread,discard-thread,promote-thread-to-tree,finalize-promotion,discard-promotion,multi-agent-debate,materialize-context,verify-tree}

# Remove this project's registry entry (edit ~/.ai/projects.yaml by hand — the
# registry is shared across projects so mass-editing is unsafe).
${EDITOR:-vi} ~/.ai/projects.yaml
```

Every commit the pack ever made is conventional-commits style and scoped by thread or leaf slug, so reverting the history is straightforward if that is what you need instead of a clean uninstall.

## AI-assisted install (copy-paste prompt)

If you want to hand the install to your coding agent, paste this entire prompt — it references this file as the authoritative procedure:

> Install the `project-brain` skill pack from `<repo-url>` into my current project. Follow `INSTALL.md` in the pack repo exactly — it is the authoritative install procedure. Before starting, read `README.md`, `CONVENTIONS.md`, and every `skills/*/SKILL.md` in the pack so you understand what you are installing. Use the Claude Code layout if you are running inside Claude Code; otherwise use the generic layout and tell me which you chose. After install, run `verify-tree` (or the equivalent manual walk if your runtime cannot invoke skills directly) and report the result. Do not modify any pack file during install.
