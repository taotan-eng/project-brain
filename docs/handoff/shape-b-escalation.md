# Shape B Escalation — Plugin spec deltas vs working assumptions

- **Raised:** 2026-05-19
- **Reporter:** Claude Code (claude-opus-4-7) executing the Shape B implementation spec
- **Branch:** `v1.0/shape-b-mcp-anchored-plugin` (created off `origin/main`, no commits yet)
- **Triggering escalation criteria** (from spec): both fired
  - "MCP-server registration isn't in plugin.json but in a separate file" — **partially true**: lives in `.mcp.json` at plugin root **OR** can be inline in `plugin.json` (so the spec's intent is achievable); the key name is `mcpServers` (camelCase), not `mcp_servers` (snake_case)
  - "there's no brew-install bootstrap field" — **fully true**: no such field documented anywhere in the plugin spec

## What the docs actually say (verbatim)

Fetched 2026-05-19 from:
- https://code.claude.com/docs/en/plugins (overview)
- https://code.claude.com/docs/en/plugins-reference (full schema)

### 1. MCP server registration

From plugins-reference § "MCP servers" (line 151+ of the fetched page):

> **Location**: `.mcp.json` in plugin root, or inline in plugin.json
>
> **Format**: Standard MCP server configuration
>
> ```json
> {
>   "mcpServers": {
>     "plugin-database": {
>       "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
>       "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
>       "env": {
>         "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
>       }
>     }
>   }
> }
> ```

From the complete-schema table in plugins-reference § "Component path fields":

> | `mcpServers` | string\|array\|object | MCP config paths or inline config | `"./my-extra-mcp-config.json"` |

**Key name is `mcpServers` (camelCase).** Server-entry shape: `command` (string), `args` (array), `env` (object), `cwd` (optional string). Variable substitution: `${CLAUDE_PLUGIN_ROOT}` and `${user_config.KEY}` for `userConfig`-declared values.

### 2. Brew-install / system-binary bootstrap

**No such field exists.** Grepping the full plugins-reference page for `homebrew|brew install|bootstrap|prerequisite|prereq|install.*binary|system dep|requires.*executable` returns only:

> **You must install the language server binary separately.** LSP plugins configure how Claude Code connects to a language server, but they don't include the server itself. If you see `Executable not found in $PATH` in the `/plugin` Errors tab, install the required binary for your language.

(LSP-servers section, line 259 of the fetched page. Same model applies to MCP servers — the plugin configures *how to connect*; it doesn't bootstrap the binary.)

Plugins do have a `dependencies` array, but it refers to **other Claude Code plugins**, not OS packages:

> | `dependencies` | array | Other plugins this plugin requires, optionally with semver version constraints. See [Constrain plugin dependency versions](/en/plugin-dependencies) | `[{ "name": "secrets-vault", "version": "~2.1.0" }]` |

There is no `requires.brew_formula`, no `homebrew_tap`, no `system_dependencies`, no `pre_install` hook documented.

### 3. plugin.json required fields

From plugins-reference § "Required fields":

> If you include a manifest, `name` is the only required field.

Everything else (`displayName`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `dependencies`, `userConfig`, etc.) is optional.

## Implication for Shape B

The Shape B design as specified relies on two assumptions:

1. **MCP-server registration via plugin.json's `mcp_servers` key** → reality is `mcpServers` (camelCase), and it can be inline in plugin.json **or** in a sibling `.mcp.json` file. This is a one-token correction (`mcp_servers` → `mcpServers`); the spec's intent works.

2. **Brew-install bootstrap via a `requires.brew_formula` (or equivalent) declaration** → there is no such field. Sub-decision 2 in `mcp-only-refactor/artifacts/0002` claims this was "verified yes 2026-05-18"; the current spec text says exactly that. **But the public plugin docs as of 2026-05-19 do not expose any bootstrap mechanism.** If the verification was real, it's against an unreleased / beta / private path that isn't reflected in code.claude.com/docs.

## Decision needed

This is a routing decision for Tom. Three paths I can see; pick one (or specify a different one):

### Option A — Ship Shape B without auto-bootstrap; document the prerequisite

Lean into the LSP-style model: the plugin's `mcpServers` field registers the server, and the README/plugin-description tells the user to install `project-brain-mcp` first via `brew install ai-project-brain/project-brain/project-brain-mcp`. The `/plugin install` step then just wires the registration; if `project-brain-mcp` isn't on PATH, Claude Code surfaces `Executable not found in $PATH` in the Errors tab and the user runs the brew install command.

- Pro: ships in this cycle; matches how every LSP plugin in the official marketplace works today.
- Pro: still a clear improvement over today (slash-command mirror files go away; cross-host install story is unified around the MCP server).
- Con: not literally "one-click" — there's a two-step install (brew first, then `/plugin install`). README has to spell this out.
- Con: sub-decision 2 said "verified yes" for bootstrap; this option walks that back. Worth confirming whether the verification source is something I'm missing.

### Option B — Re-verify sub-decision 2 before proceeding

Pause Shape B. Tom finds where sub-decision 2's "verified yes 2026-05-18" came from (a Claude Code source-code read? a private spec discussion? an unmerged feature branch?) and either:
- Reports the actual mechanism so this implementation can use it, or
- Confirms the verification was about something else (e.g., `userConfig`-prompted install instructions, not auto-bootstrap), and Shape B downgrades to Option A.

- Pro: avoids shipping on a wrong-shape assumption.
- Con: blocks the v1.0 cycle.

### Option C — Defer Shape B to v1.1; ship v1.0 final with the existing skill-pack plugin shape

Keep the current plugin.json + commands/ + skills/ layout. Fix only the canonical-repo-URL and version-string drift in plugin.json + marketplace.json. Defer the MCP-anchored refactor until the plugin spec adds bootstrap support (or until a different bootstrap path surfaces).

- Pro: zero risk to v1.0 final; refactor moves to a clean v1.1 chunk.
- Con: leaves 17 redundant slash-command files in the repo; the cross-host install asymmetry persists.

## My read

**Option A is the right shape for v1.0 ship.** The brew bootstrap was a nice-to-have; the core Shape B benefits (Claude Code's plugin system actually using the MCP server, the commands/ mirror duplication going away, the canonical-URL fix) all still land. The "two-step install" framing is the same model every LSP plugin in the marketplace uses today, so it's not novel friction.

But **I want Tom's call** before proceeding because:
- The spec was explicit about both fields being expected.
- Sub-decision 2 claimed verification — that needs reconciling. If there's a real bootstrap mechanism I missed (e.g., in unreleased docs, an SDK helper, or `userConfig` with a post-install script), Option A is leaving capability on the floor.
- Either way, the README + INSTALL.md rewrites differ between Option A (two-step) and the original spec (one-click).

## What's on disk right now

- Branch `v1.0/shape-b-mcp-anchored-plugin` created off `origin/main` (clean, no commits).
- No changes to plugin.json, marketplace.json, commands/, bin/project-brain, README.md, INSTALL.md.
- No rc.8 tag.
- Tap repo untouched (still rc.7).

Pause here until decision lands.

---

## Resolution (2026-05-19)

**Tom chose Option A.** Per `mcp-only-refactor/artifacts/0003`:
- Drop `requires.brew_formula` from plugin.json — the field doesn't exist in Claude Code's spec.
- Document the two-step install in README under an "Install in Claude Code" section.

Implementation continues with Tasks 2–12. Plugin.json uses `mcpServers` (camelCase, inline) for the MCP server registration. README explicitly walks through the two-step install (brew install → /plugin install). No auto-bootstrap; users see the LSP-style "binary must be on PATH" model.

This file is retained for audit.
