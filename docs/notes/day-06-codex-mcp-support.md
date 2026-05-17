# Day-6 Codex MCP Support Research

- Generated: 2026-05-16T15:00:00Z
- Researcher: Claude Code (claude-opus-4-7)
- Sources consulted:
  - https://modelcontextprotocol.io/clients — MCP Example Clients list (visited 2026-05-16). Codex is listed: `<McpClient name="Codex" homepage="https://github.com/openai/codex" supports="Resources, Tools, Elicitation" instructions="https://developers.openai.com/codex/mcp/">`. Note the absence of "Prompts" from the supports list — see § Known limitations.
  - https://developers.openai.com/codex/mcp/ — official OpenAI Codex CLI MCP integration docs (visited 2026-05-16). Documents TOML config shape and the `codex mcp add` CLI command.
  - https://github.com/openai/codex — Codex CLI repo README (visited 2026-05-16). Confirms Codex is a "lightweight coding agent that runs in your terminal" installable via npm or Homebrew.

## Summary

**READY.** OpenAI Codex CLI ships native MCP support over stdio. Config lives in TOML at `~/.codex/config.toml` (user-scope) or `.codex/config.toml` (project-scope, trusted projects only). The shape is well-documented in the official `developers.openai.com/codex/mcp/` page and supports `command`/`args`/`env` plus `env_vars` for env-variable forwarding. No tier gating documented. Day-6 ships a working `## OpenAI Codex CLI config` section in `INSTALL.md`.

## Findings

### SDK / version support

- Codex CLI version that ships MCP: stable / current. The MCP integration page is on the production `developers.openai.com` docs site (not behind a beta flag), so it's the supported user-facing path as of 2026-05-16.
- MCP SDK version it ships against: not explicitly listed on the docs page. Compatible with the canonical MCP SDK's stdio transport (verified by the fact that the canonical `[mcp_servers.<name>]` TOML shape with `command`/`args` matches the same stdio launch contract every other MCP client uses).
- Stdio transport supported: **yes**. The docs explicitly distinguish "STDIO Server Configuration" from "HTTP Server Configuration"; both are first-class.

### Config location and shape

- Path: `~/.codex/config.toml` (user-scope) or `.codex/config.toml` (project-scope, trusted projects only).
- Format: **TOML** (not JSON like Claude Desktop).
- `mcpServers` equivalent key: `[mcp_servers.<server-name>]` (sectioned TOML table, kebab-case server names).
- Example snippet:

    ```toml
    [mcp_servers.project-brain]
    command = "uvx"
    args = ["project-brain-mcp"]

    [mcp_servers.project-brain.env]
    PROJECT_BRAIN_HOME = "/absolute/path/to/your/project-root"
    ```

- Alternative: the CLI command `codex mcp add project-brain -- uvx project-brain-mcp` adds the entry programmatically without manual config-file editing.

### Auth / tier requirements

- Free tier: supported (no explicit tier gating documented for MCP config).
- Plus / Pro / Team / Enterprise: same path; no tier-specific behavior documented for MCP.
- API key requirements separate from CLI login: none beyond whatever the Codex CLI itself requires for its base operation (the user logs into Codex CLI normally; MCP config sits on top).

### Known limitations

- Prompt support: **not listed**. The MCP clients page lists Codex's supported features as `Resources, Tools, Elicitation` — `Prompts` is conspicuously absent. project-brain ships 17 prompts (auto-discovered from `skills/`); these will appear in `prompts/list` but Codex may not surface them to the user. Tools (the everyday lifecycle operations) will work normally.
- Resource support: **yes** (`Resources` listed). The 3 brain:// resources (thread-index, current-state, CONVENTIONS) should be readable.
- Tool annotations / progress notifications: not enumerated. Treat as best-effort — project-brain doesn't depend on either.
- Elicitation: **yes** (`Elicitation` listed). project-brain v1.0 doesn't use the elicitation flow.
- Project-scope config (`./.codex/config.toml`) requires the project to be marked "trusted" by Codex — Codex's own trust model. For chat-app-style single-brain users, the user-scope `~/.codex/config.toml` is the path of least resistance.

## Recommendation for INSTALL.md Codex section

**READY** — ship a working config snippet, mark as supported. The Codex integration is stable enough to document without an "experimental" caveat. Add a single line noting that **prompts may not appear** in Codex's UI even though the server registers them (per `Prompts` absence from the supports list); tools and resources work normally. Day-8 will run the E2E demo and validate this.
