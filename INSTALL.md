# Installing the `project-brain` skill pack

Two install paths, depending on how you'll use the pack:

- **MCP server (Claude Desktop / Claude Code / any MCP client)** — one command, no clone. Recommended for end users. See `## Install` below.
- **Manual pack install (development / Cowork / bash-script users)** — clone the repo, point your host runtime at it. See `## Manual pack install (development / Cowork users)` further down.

This file is the **authoritative install procedure** for the pack. The steps below are numbered and deterministic so that either a human or an AI agent can follow them unambiguously. If anything in the top-level `README.md` appears to disagree with this file, **this file wins**.

Tier note: works on Claude Desktop Pro and Free (config-edit path below). Max users will get a one-click Cowork marketplace install later; for now follow the Pro/Free instructions.

## Install

### macOS — Homebrew (recommended)

```bash
brew tap ai-project-brain/project-brain
brew install project-brain-mcp
```

This installs the `project-brain-mcp` binary on your PATH. **Claude Code** users complete the install with `/plugin install ai-project-brain/project-brain` (registers the MCP server with Claude Code). Chat-app hosts (Claude Desktop, Codex CLI, ChatGPT Desktop) need a config edit — see the per-host sections below.

### Other platforms — `pipx` fallback

If you're on Linux / Windows or prefer not to use Homebrew:

```bash
pipx install project-brain-mcp
```

This requires `pipx` (and on Windows / non-stock-Python systems, may require `uv` or `uvx`). Outcomes are identical to the Homebrew install: `project-brain-mcp` ends up on PATH. Plain `pip install --user project-brain-mcp` is also fine if you don't have `pipx`.

### Developer install (editable)

For working on the package itself:

```bash
pipx install --editable /path/to/project-brain/mcp
```

Edits to the source tree take effect on the next stdio session. Note that `pipx install --force` overrides any brew-installed binary on PATH; to switch back to brew, run `pipx uninstall project-brain-mcp`.

### Non-Homebrew fallback (uvx, no install)

If you don't want anything persistent on disk:

```bash
uvx project-brain-mcp
```

`uvx` runs the server in a temporary isolated environment each time it's invoked. Install `uv` first if needed: `curl -LsSf https://astral.sh/uv/install.sh | sh`. Useful for one-shot trials; for daily use, prefer `brew install` (macOS) or `pipx install` (everywhere).

## Where the brain lives — two install models

`project-brain` works in two operational shapes depending on which host you point at the MCP server. Pick the one that matches your host before reading the per-host config sections below.

| Host class | Examples | Has a project root? | What `PROJECT_BRAIN_HOME` names |
|---|---|---|---|
| **CLI tools** | Claude Code, OpenAI Codex CLI | Yes — the cwd is the project root | Auto-detected from cwd at MCP-server launch. The brain at `<cwd>/project-brain/` is used. Per-project. |
| **Chat apps** | Claude Desktop (Pro / Free / Max), ChatGPT Desktop (Plus) | No — chat surfaces, not IDEs | Set explicitly as an env var in the host's MCP config. Value is the **project root** (the parent of `project-brain/`), NOT the brain dir itself. One designated project for the lifetime of the app session. |

**CLI tools (per-project model)**

You launch `claude-code` (or `codex`) inside a repo. The MCP server is spawned per CLI session. The brain at `<cwd>/project-brain/` is detected automatically; you don't need to set `PROJECT_BRAIN_HOME`. Want the override? Pass it explicitly via the CLI tool's MCP server config or shell env before invocation — and remember the value is the project root, not the `/project-brain` subdir.

**Chat apps (single-brain model)**

Claude Desktop and ChatGPT Desktop have no filesystem-project concept. UI-level features like "Claude Projects" or "ChatGPT Projects" are chat containers, not directories — the MCP server can't see them. So in these hosts you pick **one canonical project root** ("my work folder") and point the MCP config at it via `PROJECT_BRAIN_HOME`. The brain at `<PROJECT_BRAIN_HOME>/project-brain/` serves resources (`brain://thread-index`, etc.) for the whole app session. Do NOT include `/project-brain` in the env value — the server appends it.

**Multi-brain workflows in chat apps** — for routine multi-brain use, the **recommended pattern is multiple `mcpServers` entries**, one per brain. See § "Multi-brain setup (chat apps)" below. For one-off cross-brain operations, MCP tools also accept `brain` as a per-call argument so an agent can pass `brain=<other-path>` to operate on a non-default brain without reconfiguring; the env-set brain stays the default and the only one visible to MCP resources.

**Same user, multiple hosts**: it's normal to have **both**. A developer typically runs Claude Code per-repo (per-project brains, auto-detected) AND has Claude Desktop pointing at their canonical "main brain" via the config. Each host gets its own MCP server instance with its own `PROJECT_BRAIN_HOME`. They don't interfere.

The per-host config sections below show the **chat-app pattern** explicitly (env var in the config snippet). CLI hosts that auto-detect can usually omit the `env` block from the snippet — see each host's notes.

### Resolution chain

When a tool needs a project root and the agent didn't pass `target` / `brain` explicitly, the server resolves it through this chain. First hit wins:

1. Explicit `target` / `brain` argument from the agent's tool call.
2. `$PROJECT_BRAIN_HOME` (the MCP-config env var — chat-app default).
3. `$COWORK_WORKSPACE_FOLDER` (Cowork sets at session start).
4. `$CODEX_PROJECT_ROOT` (OpenAI Codex CLI).
5. `$CLAUDE_PROJECT_ROOT` (Claude Code CLI).
6. The nearest ancestor of `cwd` that contains a `.git/` directory.
7. The last-used root cached at `~/.config/project-brain/last-used-root.txt` (written automatically after the first successful `init_project_brain`).
8. If nothing matches, the tool returns a structured `validation_error` whose hint lists every source tried.

Most chat-app users only need step 2 — set `PROJECT_BRAIN_HOME` in `mcpServers.env` and never think about the rest. CLI users get steps 4/5/6 for free from their host. Cowork users get step 3 for free. The cache (step 7) means even a misconfigured env still resolves correctly once the user has run `init_project_brain` once.

Each value is post-validated: a path ending in `/project-brain` is rejected with a hint that points at the parent dir (the brain itself lives at `<root>/project-brain/`, so the env should name the parent).

## Claude Desktop config

Edit Claude Desktop's MCP config file and add a `project-brain` entry under `mcpServers`. The config file lives at:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Paste in this snippet (merge into your existing `mcpServers` if you already have one):

```json
{
  "mcpServers": {
    "project-brain": {
      "command": "project-brain-mcp",
      "args": [],
      "env": {
        "PROJECT_BRAIN_HOME": "/absolute/path/to/your/project-root"
      }
    }
  }
}
```

`PROJECT_BRAIN_HOME` tells the server where your **project root** lives. The brain itself sits at `<root>/project-brain/`. The MCP server appends the `/project-brain` suffix automatically — do NOT include it in the env value. If you don't have a brain yet, set `PROJECT_BRAIN_HOME` to the directory where you want one and ask the agent to run `init_project_brain` — it'll create `<root>/project-brain/` for you.

After editing the config, fully quit and re-launch Claude Desktop. The MCP server is loaded at app startup; live reload does not pick it up.

#### If you prefer not to use Homebrew

For pipx / pip / uvx installs, replace the `"command"` and `"args"` fields with the appropriate invocation. The `env` block is unchanged.

```json
{
  "mcpServers": {
    "project-brain": {
      "command": "uvx",
      "args": ["project-brain-mcp"],
      "env": {
        "PROJECT_BRAIN_HOME": "/absolute/path/to/your/project-root"
      }
    }
  }
}
```

For a `pipx install project-brain-mcp` install, use `"command": "project-brain-mcp", "args": []` (same as the Homebrew form) — pipx puts the binary on PATH at `~/.local/bin/`, which Claude Desktop should find.

## ChatGPT Desktop

Deferred to v1.1. ChatGPT's MCP connectors run from OpenAI's infrastructure and can't reach a self-hosted MCP server on localhost; a public tunnel (ngrok / Cloudflare Tunnel) is required, which is out of scope for v1.0's target audience. The open question for v1.1 is whether any ChatGPT tier supports local-connector access without a tunnel. See the project's v1.1 roadmap.

## OpenAI Codex CLI config

OpenAI Codex CLI ships native MCP support over stdio. **No tier gating** — works on Free and paid plans. Per-host research note: `docs/notes/day-06-codex-mcp-support.md`.

### Config file path

- **User-scope** (recommended for chat-app-style single-brain workflows): `~/.codex/config.toml`
- **Project-scope** (per-trusted-project): `.codex/config.toml` at the project root. Codex's trust model gates project-scope; user-scope is the path of least resistance.

### Config snippet

Add this block to `~/.codex/config.toml` (TOML format, NOT JSON — different from Claude Desktop's `mcpServers` config):

```toml
[mcp_servers.project-brain]
command = "project-brain-mcp"
args = []

[mcp_servers.project-brain.env]
PROJECT_BRAIN_HOME = "/absolute/path/to/your/project-root"
```

Same `PROJECT_BRAIN_HOME` semantics as Claude Desktop: it names the **project root** (NOT the `project-brain/` subdir — the server appends `/project-brain` automatically).

Alternatively, add via the CLI without manual TOML editing:

```bash
codex mcp add project-brain -- project-brain-mcp
```

Then edit `~/.codex/config.toml` to add the `[mcp_servers.project-brain.env]` block with `PROJECT_BRAIN_HOME`, or set the env var globally in your shell profile.

### If you prefer not to use Homebrew

For pipx / uvx installs, replace `command = "project-brain-mcp"` with the appropriate invocation. The `[mcp_servers.project-brain.env]` block is unchanged.

```toml
[mcp_servers.project-brain]
command = "uvx"
args = ["project-brain-mcp"]

[mcp_servers.project-brain.env]
PROJECT_BRAIN_HOME = "/absolute/path/to/your/project-root"
```

For a `pipx install project-brain-mcp` install, the original `command = "project-brain-mcp"` form (no args) works as-is — pipx puts the binary on PATH at `~/.local/bin/`, which `codex` should find.

### Restart

Codex reloads MCP config on the next `codex` invocation — no daemon, no app to restart. Open a new terminal session (or just run `codex` again) and the new server is available.

### Known limitation: prompts may not surface

The [MCP clients page](https://modelcontextprotocol.io/clients) lists Codex's supported feature set as **Resources, Tools, Elicitation** — `Prompts` is conspicuously absent. project-brain ships 17 prompts (auto-discovered from `skills/`). These will appear in `prompts/list` and Codex will see them, but Codex may not surface a UI to invoke them. The 17 **tools** (the everyday lifecycle operations) and the 3 **resources** (`brain://thread-index` etc.) work normally.

If you want the prompt bodies as guidance text while using Codex, invoke the `run_skill(name)` tool — it returns the corresponding SKILL.md body as a string. That works on any MCP client because it's a tool, not a prompt.

## Multi-brain setup (chat apps)

If you maintain more than one brain — for example, a `work` brain and a `personal` brain, or one brain per major project — and you want them all available from a single chat app session, the **recommended pattern is multiple `mcpServers` entries**, one per brain. The same MCP server binary runs as multiple processes under distinct names, each with its own `PROJECT_BRAIN_HOME`.

This is the cleanest UX for routine multi-brain use because each brain gets its own clean namespace for tools AND its own resources (`brain://thread-index`, etc.). The agent sees clearly which brain it's operating on, and resources don't collide.

**Config snippet — Claude Desktop with two brains:**

```json
{
  "mcpServers": {
    "project-brain-work": {
      "command": "uvx",
      "args": ["project-brain-mcp"],
      "env": {
        "PROJECT_BRAIN_HOME": "/Users/you/work"
      }
    },
    "project-brain-personal": {
      "command": "uvx",
      "args": ["project-brain-mcp"],
      "env": {
        "PROJECT_BRAIN_HOME": "/Users/you/personal"
      }
    }
  }
}
```

Add as many entries as you have brains. Each must have a **unique server name** (the JSON key — here `project-brain-work` vs `project-brain-personal`). The `PROJECT_BRAIN_HOME` values are absolute paths to each **project root** (NOT the `project-brain/` subdir — the server appends that automatically). For each entry, the brain on disk is at `<PROJECT_BRAIN_HOME>/project-brain/`.

**How the agent picks the right brain.** Claude Desktop (and most MCP-capable chat apps) namespace tools by server name in the form `mcp__<server-name>__<tool-name>`. So the agent sees two distinct tool surfaces: `mcp__project-brain-work__new_thread` and `mcp__project-brain-personal__new_thread`. When you say "create a thread in my work brain," the agent calls the work-server tool; "in my personal brain" → the personal-server tool. The naming is descriptive enough that the picking is reliable.

**Resources per brain.** Each MCP server exposes its own `brain://thread-index`, `brain://current-state`, `brain://CONVENTIONS`. The full URIs become `mcp://project-brain-work/brain://thread-index` and `mcp://project-brain-personal/brain://thread-index` in the host's resource browser. Resources are silo'd — there's no cross-brain leak.

**Trade-offs:**

- **RAM cost**: each server is ~30 MB resident. Five brains = roughly 150 MB while Claude Desktop is running. Negligible on modern machines.
- **Tool-name verbosity**: in the agent's tool list, names get longer. Not a UX problem in practice because the agent's tool selection is based on intent matching, not name length.
- **Setup effort**: one-time edit of the JSON file. No per-brain code.
- **Brain count practical ceiling**: ~10 brains. Beyond that, a registry-based approach (planned for v1.1) would be cleaner.

**Naming convention.** Use `project-brain-<short-alias>` for each entry. Short aliases (`work`, `personal`, `research`, `client-a`) work better than verbose ones because the agent often surfaces the server name in dialogue and shorter is clearer. Avoid spaces and special characters in the alias.

**When NOT to use multi-server:**

- You have only one brain — use the single-`project-brain` entry from § "Claude Desktop config" above.
- You only occasionally need to cross brains — use the per-call `brain=<path>` argument on tools instead. The default-brain server handles the majority of calls; the override handles the exception. Lower overhead than running N servers.
- You're working in a CLI host (Claude Code, Codex CLI) — those auto-detect per-project brains by cwd. Don't multi-config them; just `cd` into different repos.

**Apply the same pattern to ChatGPT Desktop** (week-2 work). Once `## ChatGPT Desktop config` lands, the multi-server pattern transfers verbatim — only the config file path differs.

## Verify

Three steps to confirm the install is working. Each is independent — if step 1 passes, the rest will too.

1. **Confirm the package imports.** Run from a terminal:

    ```bash
    python3 -c "import project_brain_mcp; print(project_brain_mcp.__version__)"
    ```

    Expected output: `0.1.0` (or whatever version you installed). A `ModuleNotFoundError` here means the install didn't land in the Python path Claude Desktop will use; check `which python3` and `which project-brain-mcp`.

2. **Initialize a brain (only if you don't have one yet).** Open a new chat in Claude Desktop and prompt — that's the entire user input:

    > init project brain

    The agent calls `init_project_brain` with zero arguments. The server resolves the target via the resolution chain (PROJECT_BRAIN_HOME wins for chat apps; see § "Resolution chain") and derives the primary-project alias as kebab-case of the resolved root's leaf. After it reports success, check the filesystem:

    ```bash
    ls "$PROJECT_BRAIN_HOME/project-brain/"
    ```

    Expected: `CONVENTIONS.md`, `config.yaml`, `thread-index.md`, `current-state.md`, `threads/`, `tree/`, `archive/`. If `init_project_brain` reports a `validation_error` with "Brain already exists", a brain is already scaffolded at the resolved location — skip this step.

3. **Ask the agent to list your threads.** Open a new chat in Claude Desktop and prompt:

    > List my threads.

    The agent should call the `list_threads` tool with no `brain` argument and show whatever threads exist under `$PROJECT_BRAIN_HOME/project-brain/threads/`. The server reads `PROJECT_BRAIN_HOME` from the MCP config's `env` block; you don't need to tell the agent where the brain is. An empty list against a fresh brain is still a successful call.

4. **Ask the agent to create a thread.** In the same chat (no path needed — the server uses `$PROJECT_BRAIN_HOME` automatically):

    > Create a thread called "install test" with purpose "verifying the MCP install."

    Same pattern — no path in the prompt, no `brain` argument needed. The agent calls `new_thread` with just the slug / title / purpose; the server resolves the brain to `<$PROJECT_BRAIN_HOME>/project-brain/`. After it reports success, check the filesystem:

    ```bash
    ls "$PROJECT_BRAIN_HOME/project-brain/threads/install-test/"
    ```

    Expected: `thread.md`, `decisions-candidates.md`, `open-questions.md`. If those files are there, the roundtrip works end-to-end.

If any step fails, check `~/Library/Logs/Claude/mcp.log` (macOS) or the equivalent on your OS for server-side errors. Common issues:

- `PROJECT_BRAIN_HOME` not set or points at a non-existent path — fix the config and restart.
- `uvx` not on Claude Desktop's PATH — Claude Desktop inherits PATH from your login shell at launch time; if you installed uv in a non-default location, give the full path in `"command"`.
- The brain directory is missing required files — run the `init_project_brain` tool against an empty target dir to scaffold one.

---

## Manual pack install (development / Cowork users)

The rest of this file documents the legacy manual install — cloning the repo into a host runtime that loads bash scripts and SKILL.md prompts directly (Cowork, raw Claude Code with on-disk plugins, etc.). For most v1.0 end users the MCP server path above is simpler. Keep reading only if you're developing the pack or running it on a host without MCP support.

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
[ -f ~/.config/project-brain/projects.yaml ] || echo "# project-brain registry" > ~/.config/project-brain/projects.yaml
```

## Install procedure

### The fastest path — Claude plugin install

If you're on Claude Code 2.1+ or Claude Cowork, the pack installs as a native plugin and skips Steps 1 and 2 below entirely:

```sh
# Claude Code CLI
claude plugin marketplace add taotan-eng/project-brain
claude plugin install project-brain@project-brain
claude plugin list         # project-brain@project-brain should be enabled
```

Claude Cowork's in-app plugin browser (Settings → Extensions) currently surfaces only Anthropic- and partner-curated plugins, so `project-brain` isn't installable from the Cowork UI yet. Cowork users on the same machine as a Claude Code install will pick up the plugin automatically after the CLI install above; otherwise fall back to the manual procedure below.

After a successful plugin install, jump straight to **Step 3 — Run `init-project-brain`**. The plugin runtime has placed the 14 skills where it finds them; you do **not** need to `cp -R` anything.

**If your runtime does not support plugins** (older Claude Code, Codex, Cursor, Gemini CLI, Aider, Ollama, etc.), follow the manual procedure below.

### Step 1 — Obtain the pack (manual install only)

```sh
# Pick a scratch location. Anywhere outside the project you're installing into.
PACK_SRC="/tmp/project-brain-pack"
rm -rf "$PACK_SRC"
git clone <repo-url> "$PACK_SRC"
```

Replace `<repo-url>` with the pack's GitHub URL.

### Step 2 — Place the skills where your runtime will find them (manual install only)

The pack ships as `skills/`, `assets/`, `scripts/`, and `CONVENTIONS.md`. Where these go depends on which agent runtime you are installing into. Pick **exactly one** of the following layouts:

#### 2a. Claude Code layout (recommended for Claude Code users)

```sh
cd <your-project-root>
mkdir -p .claude/skills
cp -R "$PACK_SRC/skills/"*   .claude/skills/
# CONVENTIONS.md and supporting assets/scripts land alongside the future brain:
mkdir -p thoughts
cp    "$PACK_SRC/CONVENTIONS.md" project-brain/CONVENTIONS.md
cp -R "$PACK_SRC/assets"         project-brain/.pack-assets
cp -R "$PACK_SRC/scripts"        project-brain/.pack-scripts
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
cp    "$PACK_SRC/CONVENTIONS.md" project-brain/CONVENTIONS.md
cp -R "$PACK_SRC/skills"         project-brain/.pack-skills
cp -R "$PACK_SRC/assets"         project-brain/.pack-assets
cp -R "$PACK_SRC/scripts"        project-brain/.pack-scripts
```

To "invoke" a skill in this layout, open `project-brain/.pack-skills/<skill-name>/SKILL.md` in your agent and ask it to follow the Process section.

### Step 3 — Run `init-project-brain`

This is the only skill that runs before the brain is scaffolded; every other skill refuses until `project-brain/CONVENTIONS.md` exists. You ran step 2 which puts CONVENTIONS.md in place, so init can now complete the rest of the scaffold.

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
grep -A5 "^$(basename $(cd .. && pwd)):" ~/.config/project-brain/projects.yaml
# (Or grep for whatever alias you chose during init — it's case-sensitive.)
```

The install is complete when:

1. `project-brain/` exists at the project root.
2. `project-brain/CONVENTIONS.md` is present and its version frontmatter matches the pack's current version.
3. `project-brain/tree/NODE.md` exists, plus one `NODE.md` per top-level domain you configured.
4. `project-brain/thread-index.md` and `project-brain/current-state.md` exist.
5. `~/.config/project-brain/projects.yaml` contains your new project's entry with a `brain:` path pointing at `project-brain/` and a `remotes:` list with at least one entry.
6. The bootstrap commit is on your current branch (not pushed unless you asked `init` to push).
7. `verify-tree` exits 0.

## Upgrading a prior install

This pack is pre-1.0; upgrades may require manual migration. The rule of thumb:

1. Read `CONVENTIONS.md` Appendix A for every version between your current and target.
2. Apply schema additions (new optional frontmatter fields) by running `verify-tree` — most will pass through unchanged since the new fields are optional.
3. For required-field additions or layout changes, the changelog entry lists the migration steps. If there is no migration note, no migration is needed.

If an upgrade breaks `verify-tree`, revert `CONVENTIONS.md` to your previous version, commit, open an issue against the pack describing the break, and hold until a `repair-brain` skill lands (currently deferred).

## Uninstall

The pack has no runtime state outside `project-brain/` and `~/.config/project-brain/projects.yaml`. To uninstall:

```sh
cd <your-project-root>
# Remove the brain:
rm -rf project-brain/
# If installed at Claude Code layout, also:
rm -rf .claude/skills/{init-project-brain,new-thread,update-thread,park-thread,discard-thread,promote-thread-to-tree,finalize-promotion,discard-promotion,multi-agent-debate,materialize-context,verify-tree}

# Remove this project's registry entry (edit ~/.config/project-brain/projects.yaml by hand — the
# registry is shared across projects so mass-editing is unsafe).
${EDITOR:-vi} ~/.config/project-brain/projects.yaml
```

Every commit the pack ever made is conventional-commits style and scoped by thread or leaf slug, so reverting the history is straightforward if that is what you need instead of a clean uninstall.

## AI-assisted install (copy-paste prompt)

If you want to hand the install to your coding agent, paste this entire prompt — it references this file as the authoritative procedure:

> Install the `project-brain` skill pack from `<repo-url>` into my current project. Follow `INSTALL.md` in the pack repo exactly — it is the authoritative install procedure. Before starting, read `README.md`, `CONVENTIONS.md`, and every `skills/*/SKILL.md` in the pack so you understand what you are installing. Use the Claude Code layout if you are running inside Claude Code; otherwise use the generic layout and tell me which you chose. After install, run `verify-tree` (or the equivalent manual walk if your runtime cannot invoke skills directly) and report the result. Do not modify any pack file during install.
