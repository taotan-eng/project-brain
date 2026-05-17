# Day 8 Handoff — Native SSE transport in project-brain-mcp + brew service block

- **Audience**: Claude Code (or any agent operating on the project-brain repo)
- **Date authored**: 2026-05-17
- **Author**: Tom (taotan6@gmail.com) via planning session
- **Estimated effort**: 0.5-1 person-day
- **Status**: ready
- **Execution mode**: autonomous test-fix-retest loop; escalate only on judgment calls (see § Escalation)
- **Predecessor**: `day-07-brew-formula.md` (status: done; PR #7 merged to `main`)
- **Branch**: `day-08/native-sse-transport` (created at pre-flight)

## TL;DR

Wire ChatGPT support **without adding a Node dependency or a separate bridge daemon.** The MCP Python SDK that `project-brain-mcp` already depends on (`mcp>=1.0.0`) ships native SSE server transport via FastMCP. Adding a CLI flag to `__main__.py` lets the same binary serve stdio (for Claude Desktop / Codex / Claude Code) or SSE (for ChatGPT) depending on how it's invoked. The brew formula gains a `service do ... end` block; `brew services start project-brain-mcp` runs the SSE daemon on `127.0.0.1:8787`. No bridge formula, no npm, no wrapper script.

1. **`__main__.py` CLI flag**: `--http` (or `PROJECT_BRAIN_TRANSPORT=sse` env) flips `app.run(transport="stdio")` → `app.run(transport="sse", host="127.0.0.1", port=...)`. Default stays stdio.
2. **Port config**: `PROJECT_BRAIN_SSE_PORT` env var (default 8787). Fail-fast on collision.
3. **Tag `v1.0.0-rc.6`** since the binary changes. Formula bumps to rc.6 url + sha256.
4. **Formula gains a `service do ... end` block** that runs `project-brain-mcp --http`. `brew services start project-brain-mcp` activates it.
5. **Tap CI extension**: after the existing stdio smoke test, start the service, probe `http://localhost:8787/sse`, stop.
6. **INSTALL.md `## ChatGPT Desktop config` Step 1** becomes a single command pair: `brew install project-brain-mcp && brew services start project-brain-mcp` (no separate bridge package).
7. **compat-matrix** ChatGPT Plus+ row: `via brew install project-brain-mcp && brew services start project-brain-mcp on macOS`.

**Risk acknowledgment**: FastMCP's SSE transport is less specifically battle-tested with ChatGPT's custom-connector flow than `mcp-remote` (npm). If day-9's E2E demo fails compatibility, fall back to `mcp-remote` in v1.0.1; ship v1.0 with the native-SSE approach.

**Day-9** = ChatGPT E2E demo against the brew-installed `project-brain-mcp` SSE service.
**Day-10** = Codex E2E demo against the brew-installed `project-brain-mcp` stdio.
**Days 11-14** = Week 3 polish + final `v1.0.0` release.

## Context

You are executing **day 8 (week 2 day 3) of the project-brain v1.0 3-week release plan**.

Read these for "why" decisions:

- **Brew-install-and-daemon thread**: `/Users/ttan/workspace/Project-Brain/brew-install-and-daemon.md` — captured the Scope A vs B decision space. Scope A (server formula) landed in day-7. Day-8 was originally scoped as a separate bridge daemon (Scope B). **2026-05-17 revision**: Tom pushed back on the npm/Node dependency; the FastMCP SDK's built-in SSE transport replaces the bridge daemon entirely.
- **Day-7 close-out notes**: `docs/handoff/day-07-brew-formula.md` § "Notes for the next handoff (day-8)" mentioned a separate bridge formula; this handoff supersedes that with the native-SSE approach.
- **Day-6 INSTALL.md `## ChatGPT Desktop config`**: the section that gets rewritten. Currently uses `npx -y mcp-remote ...` in a terminal; gets replaced with `brew services start project-brain-mcp`.
- **Day-7 server formula** at `ai-project-brain/homebrew-project-brain` / `Formula/project-brain-mcp.rb`: gets edited (not duplicated) — formula bumps url+sha256 to rc.6 and adds a `service do ... end` block.
- **FastMCP SSE transport reference**: the canonical pattern is `app.run(transport="sse", host="127.0.0.1", port=8787)`. Exposes `GET /sse` for the SSE event stream and `POST /messages` for client-to-server messages. ChatGPT's "Add custom connector" UI takes the base URL ending in `/sse`.
- **Path C semantic**: `PROJECT_BRAIN_HOME` is the project root. SSE mode inherits this env var same as stdio mode; no semantic change.

Day-7 closed by landing the `project-brain-mcp` formula. Day-8 makes that same binary capable of serving HTTP/SSE so ChatGPT can connect without a separate bridge process.

## Why native SSE, not the mcp-remote bridge

Two paths were on the table:

- **Option 1 (original plan)**: Add a separate `project-brain-bridge` formula that depends on Node and invokes the `mcp-remote` npm package as a launchd service. Battle-tested against ChatGPT specifically.
- **Option 2 (chosen)**: Use FastMCP's built-in SSE transport. Same `project-brain-mcp` binary, new CLI flag. No new dependency.

**Day-8 ships Option 2.** Reasoning:

1. **No new runtime dependency.** Option 1 adds Node (~50 MB bottle increase, plus npm package surface). Option 2 reuses the `mcp` package that's already in `pyproject.toml`.
2. **Single binary, simpler ops.** Option 2 means one install, one formula, one upgrade path. Option 1 fans out into `project-brain-mcp` + `project-brain-bridge` + intra-tap dependency resolution + a wrapper script.
3. **Smaller code surface owned.** Option 1's wrapper script + launchd plist were ~50 lines but Option 2 is ~10 lines of `__main__.py` change.
4. **Architectural cleanliness.** SSE is just another transport for the same MCP server. The "bridge" concept was an accidental complexity introduced because the original day-6 thinking assumed `mcp-remote` was the canonical solution. FastMCP's native SSE makes the bridge concept unnecessary.

**Risk acknowledgment**: FastMCP's SSE transport hasn't been field-tested against ChatGPT's custom-connector flow as extensively as `mcp-remote` has. If day-9's E2E demo finds a compatibility gap, the fallback is to ship `mcp-remote` (Option 1) in v1.0.1 as a `project-brain-bridge` formula. v1.0 stdio paths (Claude Desktop, Codex, Claude Code) are unaffected either way.

## Goal

By the end of this handoff:

1. **`mcp/src/project_brain_mcp/__main__.py`** supports a `--http` CLI flag (or `PROJECT_BRAIN_TRANSPORT=sse` env var). When set, calls `app.run(transport="sse", host="127.0.0.1", port=PORT)` instead of stdio. Default invocation stays stdio (no behavioral change for Claude Desktop / Codex / Claude Code users).
2. **`PROJECT_BRAIN_SSE_PORT` env var** read at startup; default 8787. Fail-fast with clear error on port collision (no auto-fallback in v1.0).
3. **Smoke test extended** (`scripts/smoke_mcp_roundtrip.py`): in addition to the existing stdio roundtrip, a new test invokes `project-brain-mcp --http` as a subprocess, opens an SSE connection via `mcp.client.sse`, asserts `tools/list` returns ≥17 tools and `prompts/list` returns ≥14 prompts.
4. **Tag `v1.0.0-rc.6`** in the main repo (the binary changed; rc.5's tarball is stale).
5. **Formula `Formula/project-brain-mcp.rb`** in the tap: url bumped to rc.6, sha256 recomputed, NEW `service do ... end` block added. Audit passes.
6. **`brew services start project-brain-mcp`** starts the daemon on `127.0.0.1:8787`. `brew services list` shows `started`. `curl -N http://localhost:8787/sse` returns HTTP 200 + `text/event-stream` content-type.
7. **Tap CI extended**: after the existing stdio smoke step, a new step exercises the service-start path. Both steps must end green.
8. **INSTALL.md `## ChatGPT Desktop config`** rewritten:
    - **Step 1 — Start the service**: `brew install project-brain-mcp && brew services start project-brain-mcp` (assumes brew tap is already configured from day-7).
    - Verify-running mini-section: `brew services list | grep project-brain-mcp`.
    - Stop/restart mini-section.
    - Port override mini-section noting `PROJECT_BRAIN_SSE_PORT`.
    - **Step 2 — Add the connector in ChatGPT**: unchanged from day-6 (URL stays `http://localhost:8787/sse`).
9. **compat-matrix.md** ChatGPT Plus+ row's Notes column gains `Install via brew install project-brain-mcp && brew services start project-brain-mcp on macOS`. "First-session validated" stays `pending (day-9)`.
10. The **day-8 evaluation report** at `docs/handoff/day-08-evaluation-report.md` documents 8/8 merge criteria pass; the day-8 PR is open against `main` with that report as its body.

## Scope decisions (explicit, to head off creep)

**In scope for day-8:**
- `__main__.py` CLI-flag addition.
- Smoke-test extension for the SSE transport.
- v1.0.0-rc.6 tag + GitHub release.
- Formula edit in tap (bump tag, add service block).
- Tap CI extension.
- INSTALL.md ChatGPT section rewrite.
- compat-matrix ChatGPT row note update.

**Out of scope (deferred to day-9):**
- The actual ChatGPT Desktop E2E demo (real user, real ChatGPT account, real connector add, real prompt round-trip).
- compat-matrix ChatGPT "First-session validated" status update (stays `pending` until day-9 evidence captured).
- `docs/demos/day-09-chatgpt-desktop.md` evidence capture.

**Out of scope (deferred to v1.0.1 or v1.1):**
- `mcp-remote`-based bridge as a fallback formula (only revisit if day-9 finds FastMCP SSE incompatible with ChatGPT).
- Port collision auto-fallback (probe 8787-8800 range).
- `~/.project-brain/bridge.toml` or any TOML config file.
- Linux systemd unit (linuxbrew users get the formula but no service integration; manual `project-brain-mcp --http` invocation).
- Windows path entirely.
- Auth tokens for the SSE endpoint (binds to 127.0.0.1, no auth needed for v1.0).
- Multi-port (one SSE service serving multiple brains).

**Out of scope (don't touch):**
- The stdio default behavior. Existing stdio users see zero change.
- Tool/prompt/resource registration code. SSE serves the same MCP server, not a different one.
- Day-7 INSTALL.md sections (Claude Desktop, Codex CLI, Claude Code). Keep unchanged.
- Pack assets (`skills/`, `scripts/`, `assets/`, `CONVENTIONS.md`).
- The workspace-root scratch docs.

## PR-merge criteria

| # | Criterion | Programmatic check |
|---|---|---|
| 1 | `--http` flag works | `project-brain-mcp --http &` exits 0 (or starts listening); `curl --max-time 2 -o /dev/null -w "%{http_code} %{content_type}\n" http://localhost:8787/sse` returns `200 text/event-stream`. Process killable via SIGTERM. |
| 2 | `PROJECT_BRAIN_SSE_PORT` honored | `PROJECT_BRAIN_SSE_PORT=8788 project-brain-mcp --http &` binds to 8788; curl on 8788 succeeds; curl on 8787 returns connection-refused. |
| 3 | Default stdio unchanged | `project-brain-mcp` (no flag) starts in stdio mode; existing smoke test passes; tool/prompt counts unchanged from day-7. |
| 4 | SSE smoke test added + passes | `scripts/smoke_mcp_roundtrip.py` exercises both transports. SSE test connects via `mcp.client.sse` to `http://localhost:8787/sse`, asserts `tools/list >= 17` and `prompts/list >= 14`. Smoke exits 0. |
| 5 | v1.0.0-rc.6 tag + release | `git tag` lists `v1.0.0-rc.6`; `gh release view v1.0.0-rc.6` shows published release; formula references match. |
| 6 | Formula edits clean + service block valid | `brew style --fix Formula/project-brain-mcp.rb` exits 0; `brew audit --strict --formula Formula/project-brain-mcp.rb` exits 0. The `service do ... end` block uses the modern DSL (not deprecated `plist do`). |
| 7 | Service starts + SSE responds via brew | `brew install` from updated formula succeeds. `brew services start project-brain-mcp` shows `started` in `brew services list`. Within 5s, `curl -N --max-time 2 http://localhost:8787/sse` returns 200 + SSE content-type. `brew services stop` cleans up. |
| 8 | INSTALL.md + compat-matrix updates correct | `## ChatGPT Desktop config` Step 1 uses `brew services start project-brain-mcp` (no `npx`, no `mcp-remote`). Other INSTALL.md sections (Claude Desktop, Codex, Claude Code, Where the brain lives, Multi-brain) byte-identical to day-7. compat-matrix ChatGPT Plus+ row Notes contains `brew install project-brain-mcp && brew services start project-brain-mcp`. |

Workflow:

- Working branch is `day-08/native-sse-transport` off `main`.
- Main-repo commits use Conventional Commits with scope (e.g. `feat(mcp): add SSE transport via --http flag`, `feat(formula): add service block`, `docs(install): swap mcp-remote for brew services`).
- Tap-repo commits live in `ai-project-brain/homebrew-project-brain`. Their SHAs + CI run URL referenced from the eval report.
- After MERGE-READY, branch is pushed; PR opened against `main` with `docs/handoff/day-08-evaluation-report.md` as body.

## Development loop

Standard. Each task: spec → execute → run validation → consult Common failure modes → ~5 retries max → escalate.

**Sequencing**: Task 1 (CLI flag in `__main__.py`) gates everything — verify it works locally before tagging rc.6. Task 5 (formula edit) depends on rc.6 existing. Tasks 7 (INSTALL.md) and 8 (compat-matrix) are independent and can run in parallel after Task 1.

## Pre-flight checks

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Right repo
test -f CONVENTIONS.md -a -d skills/ -a -f INSTALL.md -a -d mcp/ \
  || { echo "FAIL: not in pack repo"; exit 1; }

# 2. gh CLI installed and authed
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 \
  || { echo "FAIL: gh missing or unauthed"; exit 1; }

# 3. Homebrew installed
command -v brew >/dev/null 2>&1 \
  || { echo "FAIL: brew missing"; exit 1; }

# 4. Day-7 merged
git fetch origin
git merge-base --is-ancestor origin/day-07/brew-formula origin/main \
  || { echo "FAIL: day-7 not merged to main"; exit 1; }

# 5. Tap repo cloned locally (from day-7)
test -d /Users/ttan/workspace/Project-Brain/final/tap-project-brain/Formula \
  || { echo "FAIL: tap-project-brain not present"; exit 1; }

test -f /Users/ttan/workspace/Project-Brain/final/tap-project-brain/Formula/project-brain-mcp.rb \
  || { echo "FAIL: day-7 server formula missing in tap"; exit 1; }

# 6. mcp package supports SSE — sanity check
python3 -c "from mcp.server.fastmcp import FastMCP; assert hasattr(FastMCP, 'run')" \
  || { echo "FAIL: FastMCP not importable; check editable install"; exit 1; }

# 7. Branch
git checkout -b day-08/native-sse-transport origin/main
```

If any pre-flight fails, fix before starting.

## Tasks

### Task 1 — Add `--http` flag to `__main__.py`

Read the current entry point:

```bash
cat mcp/src/project_brain_mcp/__main__.py
```

It likely contains something like:

```python
from .server import app

def main():
    app.run()

if __name__ == "__main__":
    main()
```

Replace with a version that supports the `--http` flag and the `PROJECT_BRAIN_SSE_PORT` env override:

```python
"""project-brain-mcp entry point.

By default runs the MCP server over stdio. Pass --http (or set
PROJECT_BRAIN_TRANSPORT=sse) to expose the same server over
HTTP/SSE for clients like ChatGPT Desktop that don't host stdio.
"""

from __future__ import annotations

import os
import sys

from .server import app


def _is_http_mode() -> bool:
    """Return True if the user requested SSE transport.

    Accepts either:
      - CLI flag: --http  (also accepts --sse as an alias)
      - Env var: PROJECT_BRAIN_TRANSPORT=sse (case-insensitive)
    """
    if any(a in {"--http", "--sse"} for a in sys.argv[1:]):
        return True
    return os.environ.get("PROJECT_BRAIN_TRANSPORT", "").lower() == "sse"


def main() -> None:
    if _is_http_mode():
        host = "127.0.0.1"
        port_str = os.environ.get("PROJECT_BRAIN_SSE_PORT", "8787")
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError(f"port out of range: {port}")
        except ValueError as e:
            print(
                f"FATAL: invalid PROJECT_BRAIN_SSE_PORT={port_str!r} ({e})",
                file=sys.stderr,
            )
            sys.exit(2)
        # FastMCP's SSE transport binds to host:port and exposes
        # GET /sse + POST /messages per the MCP SSE transport spec.
        app.run(transport="sse", host=host, port=port)
    else:
        # Default: stdio (what every existing MCP host uses).
        app.run(transport="stdio")


if __name__ == "__main__":
    main()
```

**Key design notes:**

- The CLI-flag detection is conservative: only `--http` or `--sse` trigger SSE mode. No argparse — keeps the CLI surface minimal.
- Port validation: parse to int, range-check (1-65535), exit 2 with clear stderr message on invalid input. Don't let FastMCP get a malformed port.
- 127.0.0.1 is hardcoded. No `--host` flag for v1.0 — auth/security work is v1.1.
- The `transport="sse"` keyword arg matches FastMCP's documented API. If FastMCP raises `TypeError: run() got unexpected keyword argument 'transport'`, the SDK version is too old; check `pip show mcp` for the version and either bump the floor in pyproject.toml or use FastMCP's lower-level `app.sse_app()` method.

**Verify locally:**

```bash
# Stdio mode (default) — verify unchanged
echo "default mode:"
project-brain-mcp 2>&1 &
PID=$!
sleep 1
kill $PID 2>/dev/null
echo "stdio mode OK"

# SSE mode — start, probe, kill
echo "SSE mode:"
project-brain-mcp --http &
PID=$!
sleep 1
STATUS=$(curl --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:8787/sse)
test "$STATUS" = "200" && echo "SSE responded 200" || echo "SSE failed: $STATUS"
kill $PID 2>/dev/null
sleep 0.5

# Custom port
echo "custom port:"
PROJECT_BRAIN_SSE_PORT=8800 project-brain-mcp --http &
PID=$!
sleep 1
STATUS=$(curl --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:8800/sse)
test "$STATUS" = "200" && echo "Port 8800 responded 200" || echo "Custom port failed: $STATUS"
kill $PID 2>/dev/null
```

All three echoes must show success. If any fail, fix before continuing.

Commit:

```bash
git add mcp/src/project_brain_mcp/__main__.py
git commit -m "feat(mcp): add SSE transport via --http flag

project-brain-mcp now supports both stdio (default, used by Claude
Desktop / Codex / Claude Code) and HTTP/SSE (used by ChatGPT
Desktop). The same FastMCP server instance serves both transports;
the only difference is how the entry point invokes app.run().

CLI: pass --http or --sse to enable SSE mode.
Env var: set PROJECT_BRAIN_TRANSPORT=sse for the same effect.
Port: PROJECT_BRAIN_SSE_PORT (default 8787); fail-fast on collision
or invalid value.

No change to stdio default — existing hosts see zero behavioral
difference. SSE mode binds 127.0.0.1:8787 only (no LAN exposure)."
```

### Task 2 — Extend the smoke test for SSE transport

Edit `scripts/smoke_mcp_roundtrip.py`. After the existing stdio roundtrip, add an SSE test.

Reference shape (you may need to adapt to the actual SDK API):

```python
async def _sse_roundtrip():
    """Spawn project-brain-mcp --http in a subprocess, connect via
    mcp.client.sse, verify tools and prompts."""
    import asyncio
    import os
    import socket
    from contextlib import asynccontextmanager

    from mcp.client.sse import sse_client
    from mcp import ClientSession

    # Pick a port that's free (rotating 8800-8810 if 8787 in use locally).
    def _free_port(start=8800, end=8810):
        for p in range(start, end):
            try:
                with socket.socket() as s:
                    s.bind(("127.0.0.1", p))
                    return p
            except OSError:
                continue
        raise RuntimeError("no free port in 8800-8810")

    port = _free_port()
    env = {**os.environ, "PROJECT_BRAIN_SSE_PORT": str(port)}
    proc = await asyncio.create_subprocess_exec(
        "project-brain-mcp", "--http",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        # Wait for the server to bind (poll the port).
        for _ in range(40):  # 4 seconds total
            await asyncio.sleep(0.1)
            with socket.socket() as s:
                try:
                    s.connect(("127.0.0.1", port))
                    break
                except OSError:
                    continue
        else:
            raise RuntimeError(f"server didn't bind {port} within 4s")

        url = f"http://127.0.0.1:{port}/sse"
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                prompts = await session.list_prompts()
                assert len(tools.tools) >= 17, f"SSE: expected >=17 tools, got {len(tools.tools)}"
                assert len(prompts.prompts) >= 14, f"SSE: expected >=14 prompts, got {len(prompts.prompts)}"
                print(f"SSE roundtrip: {len(tools.tools)} tools, {len(prompts.prompts)} prompts")
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
```

Call it from the smoke test's main routine after the existing stdio roundtrip. Print `MCP SMOKE TEST PASSED` only after BOTH stdio and SSE pass.

**Run it locally:**

```bash
python3 scripts/smoke_mcp_roundtrip.py 2>&1 | tail -10
# Expect: both stdio and SSE roundtrips pass; MCP SMOKE TEST PASSED
```

If the SSE client API differs from the example shape, check the installed `mcp` package's docs: `python3 -c "import mcp.client.sse; help(mcp.client.sse.sse_client)"`.

Commit:

```bash
git add scripts/smoke_mcp_roundtrip.py
git commit -m "test(mcp): extend smoke to exercise SSE transport

After the existing stdio roundtrip, spawn project-brain-mcp --http
as a subprocess on a free port, connect via mcp.client.sse, and
assert tools/list and prompts/list return the expected counts. Both
transports must pass before the smoke test reports PASSED."
```

### Task 3 — Tag `v1.0.0-rc.6`

```bash
cd /Users/ttan/workspace/Project-Brain/final/project-brain
git tag -a v1.0.0-rc.6 -m "v1.0.0-rc.6 — native SSE transport via --http flag

project-brain-mcp gains a --http (or --sse) flag that switches from
stdio transport to HTTP/SSE transport. Same FastMCP server, same
tool/prompt/resource registry, different binding. Targets ChatGPT
Desktop which only accepts remote MCP endpoints.

This replaces the originally-planned day-8 mcp-remote bridge daemon.
No new dependencies; no new formula. The Homebrew formula bumps to
this tag and gains a 'service do ... end' block so 'brew services
start project-brain-mcp' runs the SSE daemon."

git push origin v1.0.0-rc.6

gh release create v1.0.0-rc.6 \
  --title "v1.0.0-rc.6" \
  --notes "Day-8 release candidate: native SSE transport.

project-brain-mcp now serves both stdio (default) and HTTP/SSE
(via --http flag) from the same binary. ChatGPT Desktop users will
'brew services start project-brain-mcp' to run the SSE daemon on
127.0.0.1:8787. No bridge package needed.

See INSTALL.md § 'ChatGPT Desktop config' for the install path."

# Compute the new SHA for the formula:
TARBALL_SHA=$(curl -fsL "https://github.com/ai-project-brain/project-brain/archive/refs/tags/v1.0.0-rc.6.tar.gz" | shasum -a 256 | awk '{print $1}')
echo "rc.6 TARBALL_SHA=${TARBALL_SHA}"
```

### Task 4 — Update the formula in the tap repo

Switch to the tap repo:

```bash
cd /Users/ttan/workspace/Project-Brain/final/tap-project-brain
git pull origin main
```

Edit `Formula/project-brain-mcp.rb`:

**(a) Bump `url` from `v1.0.0-rc.5` to `v1.0.0-rc.6`.**

**(b) Update `sha256`** to the value from the previous step.

**(c) Add a `service do ... end` block** before the `test do` block:

```ruby
  service do
    run [opt_bin/"project-brain-mcp", "--http"]
    keep_alive true
    log_path var/"log/project-brain-mcp.log"
    error_log_path var/"log/project-brain-mcp.error.log"
  end
```

**(d) Update the formula's description** to mention SSE capability:

```ruby
  desc "Markdown-in-git decision-tracking MCP server (stdio + HTTP/SSE)"
```

**Audit:**

```bash
brew style --fix Formula/project-brain-mcp.rb
brew audit --strict --formula Formula/project-brain-mcp.rb
```

Both must exit 0. If style auto-fix changes the file, review the diff before committing.

**Local verify:**

```bash
brew reinstall --formula ./Formula/project-brain-mcp.rb
command -v project-brain-mcp  # confirm still on PATH

# Start as a service
brew services start project-brain-mcp
sleep 2
brew services list | grep project-brain-mcp
# Expect: started

# Probe SSE
curl -sS --max-time 2 -o /dev/null -w "%{http_code} %{content_type}\n" http://localhost:8787/sse
# Expect: 200 text/event-stream

# Stop
brew services stop project-brain-mcp
```

If service fails to start or SSE doesn't respond, check the logs:

```bash
tail -30 /opt/homebrew/var/log/project-brain-mcp.error.log
```

Commit:

```bash
git add Formula/project-brain-mcp.rb
git commit -m "feat(formula): bump to rc.6 + add service block for SSE daemon

Tag v1.0.0-rc.6 in the main repo added the --http CLI flag that
serves project-brain-mcp over HTTP/SSE for ChatGPT Desktop. This
formula bump picks up that change and exposes it via the brew
services pattern: 'brew services start project-brain-mcp' runs the
SSE daemon on 127.0.0.1:8787.

stdio remains the default invocation — existing Claude Desktop /
Codex / Claude Code users see no behavioral change unless they
manually invoke 'brew services start'.

Logs land in #{var}/log/project-brain-mcp.{log,error.log}."
git push origin main
```

### Task 5 — Extend tap CI

Edit `.github/workflows/brew-formula-build.yml` in the tap repo. After the existing stdio smoke step, add a service start + SSE probe step.

```yaml
      - name: Start service + probe SSE endpoint
        run: |
          brew services start project-brain-mcp
          # Poll for up to 5 seconds for the service to bind.
          for i in 1 2 3 4 5 6 7 8 9 10; do
            if curl -sSf --max-time 1 -o /dev/null http://localhost:8787/sse; then
              echo "SSE up after ${i} attempts"
              break
            fi
            sleep 0.5
          done
          # Final probe — must return 200 + SSE content-type.
          STATUS=$(curl -sS --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:8787/sse)
          CT=$(curl -sS --max-time 2 -o /dev/null -w "%{content_type}" http://localhost:8787/sse)
          test "$STATUS" = "200" \
            || { echo "Expected 200, got $STATUS"; tail -30 "$(brew --prefix)/var/log/project-brain-mcp.log" 2>/dev/null; \
                 tail -30 "$(brew --prefix)/var/log/project-brain-mcp.error.log" 2>/dev/null; exit 1; }
          echo "$CT" | grep -qi "text/event-stream" \
            || { echo "Expected text/event-stream, got $CT"; exit 1; }
          echo "SSE OK"

      - name: Stop service (cleanup)
        if: always()
        run: brew services stop project-brain-mcp || true
```

Commit:

```bash
git add .github/workflows/brew-formula-build.yml
git commit -m "ci(tap): probe SSE endpoint after brew services start

After the existing stdio smoke test, start the service via
brew services, poll for the SSE endpoint to come up (up to 5s),
then probe it once for HTTP 200 + text/event-stream content-type.
Stop the service in always-run cleanup."
git push origin main
```

Wait for the CI run to complete; both stdio and SSE jobs must end green.

### Task 6 — Rewrite INSTALL.md `## ChatGPT Desktop config`

Switch to the main repo. Edit `INSTALL.md`.

Find the `## ChatGPT Desktop config` section. Replace **Step 1** with:

```markdown
### Step 1 — Install + start the SSE service

ChatGPT only accepts remote HTTP/SSE endpoints; it can't launch local stdio servers. project-brain-mcp's `--http` flag serves the same MCP server over HTTP/SSE on `127.0.0.1:8787` — that URL is what ChatGPT connects to.

One-time install + start:

```bash
brew install ai-project-brain/project-brain/project-brain-mcp
brew services start project-brain-mcp
```

The first command installs the server (already in place if you've used Claude Desktop or Codex CLI; brew makes it a no-op then). The second starts the SSE daemon as a managed background service via launchd. The service:

- Auto-starts at login (managed by launchd via `brew services`).
- Restarts automatically if it crashes (`KeepAlive`).
- Logs to `/opt/homebrew/var/log/project-brain-mcp.log` (and `.error.log` for stderr).
- Inherits `PROJECT_BRAIN_HOME` from your shell environment — set it in your shell profile (e.g., `~/.zshrc`) before `brew services start`.

#### Verify the service is running

```bash
brew services list | grep project-brain-mcp
# Expect: project-brain-mcp  started  ...
```

If status is `error`, check the log:

```bash
tail -30 /opt/homebrew/var/log/project-brain-mcp.error.log
```

#### Stopping / restarting / reloading config

```bash
brew services stop project-brain-mcp
brew services restart project-brain-mcp   # picks up new env vars from your shell profile
```

#### Port override

Default port is 8787. If another service uses that port, set `PROJECT_BRAIN_SSE_PORT` in your shell profile:

```bash
export PROJECT_BRAIN_SSE_PORT=8788
```

Then `brew services restart project-brain-mcp` and adjust the ChatGPT connector URL to match (Step 2 below).
```

**Step 2 — Add the connector in ChatGPT**: keep the day-6 prose largely intact. Drop any references to "the bridge process" or `npx`. The connector URL stays `http://localhost:8787/sse`.

**Tier note**: keep the day-6 Free-tier-excluded paragraph.

**Delete the obsolete "Architectural note" + "Step 1 — Run the local bridge" subsection** that explains the `npx mcp-remote ...` command.

**Same-section invariant check:**

```bash
git diff main..HEAD -- INSTALL.md | head -200
# Confirm: changes are confined to the ChatGPT section.
```

Commit:

```bash
git add INSTALL.md
git commit -m "docs(install): rewrite ChatGPT section for native SSE daemon

Step 1 collapses 'keep a terminal open with npx mcp-remote' to
'brew install project-brain-mcp && brew services start
project-brain-mcp'. The same server you use for Claude Desktop /
Codex CLI now serves ChatGPT too — just started as a launchd
service via brew.

Step 2 (Settings → Connectors → Developer mode → Add custom
connector → http://localhost:8787/sse) unchanged.

Documents verify-running check, stop/restart commands, and the
PROJECT_BRAIN_SSE_PORT override."
```

### Task 7 — Update `compat-matrix.md`

Find the ChatGPT Plus+ row. Replace its Notes column:

```
| ChatGPT Desktop | Plus, Pro, Team, Enterprise | HTTP/SSE | pending (day-9) | ChatGPT only accepts remote MCP endpoints. project-brain-mcp serves the same FastMCP server over HTTP/SSE when started via `brew services start project-brain-mcp` (the binary's `--http` flag). Install via `brew install project-brain-mcp && brew services start project-brain-mcp` on macOS; add `http://localhost:8787/sse` as a custom connector in **Settings → Connectors → Developer mode**. Free tier excluded — no custom-connector UI. See INSTALL.md § "ChatGPT Desktop config". |
```

Changes:
- Transport column: from `HTTP/SSE (via bridge)` to just `HTTP/SSE` (no bridge involved).
- Notes: swap the `npx mcp-remote ...` command for the `brew services` pair; mention the `--http` flag for transparency about how it works.

Commit:

```bash
git add compat-matrix.md
git commit -m "docs(compat): native SSE replaces mcp-remote bridge in ChatGPT row

Transport simplified from 'HTTP/SSE (via bridge)' to 'HTTP/SSE' —
the bridge concept is unnecessary now that project-brain-mcp serves
SSE natively via the --http flag. Notes column updated to reflect
the brew services install path. Pending demo date stays day-9."
```

### Task 8 — Author the evaluation report

Create `docs/handoff/day-08-evaluation-report.md` following the template at `docs/handoff/_evaluation-report-template.md`.

Frontmatter:

```yaml
- Generated: <ISO 8601 timestamp>
- Plan reference: project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md § 4 (week 2 day 3)
- Handoff: docs/handoff/day-08-brew-bridge-daemon.md
- Predecessor: day-07 (merged to main via PR #7)
- Week 2 day 3: ChatGPT support via native SSE transport (replaces planned bridge daemon)
```

Body sections (mirror day-7):

- `## Script adjustments from handoff spec` — any deviations CC made.
- `## Architecture note: native SSE chosen over mcp-remote bridge`. Brief paragraph capturing the Option 1 vs Option 2 decision from this handoff's "Why native SSE" section.
- `## Merge criteria` — 8-row table mirroring this handoff's criteria with ✓ status + evidence.
- `## Files changed (this branch vs main)` — `git diff --stat main...HEAD` for main repo.
- `## Commits (this branch)` — `git log --oneline main..HEAD`.
- `## Tap repo state` — tap CI run URL for rc.6 commit + green badge; formula version notes.
- `## Verdict` — MERGE-READY if all 8 criteria pass.

Commit:

```bash
git add docs/handoff/day-08-brew-bridge-daemon.md docs/handoff/day-08-evaluation-report.md
git commit -m "docs(handoff): stage day-8 plan + evaluation report (MERGE-READY)"
```

### Task 9 — Push and open PR

```bash
git push -u origin day-08/native-sse-transport

gh pr create \
  --base main \
  --head day-08/native-sse-transport \
  --title "Day 8: Native SSE transport — brew services replaces mcp-remote bridge" \
  --body-file docs/handoff/day-08-evaluation-report.md

gh pr checks
```

CI must be green before declaring done.

## Common failure modes

| Failure | Cause | Fix |
|---|---|---|
| `app.run(transport="sse", ...)` raises `TypeError: unexpected keyword argument 'transport'` | mcp SDK version is too old | `pip show mcp` to confirm version; bump `mcp>=1.0.0` floor in `pyproject.toml` if needed (`mcp>=1.27.0` is safe). |
| `app.run(transport="sse", ...)` raises `RuntimeError: SSE transport not supported` | FastMCP variant doesn't include SSE | Use the lower-level `app.sse_app()` method instead. Check the SDK docs for the correct invocation. |
| `--http` flag works locally but `brew services start` fails with `error` | Service uses different env / PATH than your shell | Check `error.log`. Often a missing `PROJECT_BRAIN_HOME` — service inherits the launchd-managed env, not the user's shell env. Document in INSTALL.md that env vars need to be in shell profile and `brew services restart` after changes. |
| `curl http://localhost:8787/sse` returns connection refused after `brew services start` | Service launched but not bound | Check `tail -30 /opt/homebrew/var/log/project-brain-mcp.log`. Look for `Address already in use` (port collision) or `permission denied` (rare on localhost). |
| `curl http://localhost:8787/sse` returns 200 but content-type is `text/html` or `application/json` | SSE transport not engaged; FastMCP serving the wrong endpoint | Check the URL — FastMCP's SSE endpoint may be `/messages` for POST, `/sse` for GET. The handoff assumes `/sse` for GET; if FastMCP differs, update both the curl probe and the INSTALL.md URL. |
| Smoke test SSE roundtrip times out at `session.initialize()` | Subprocess didn't bind in time, or SSE handshake has a bug | Increase the bind-poll timeout (4s → 10s); add `print(proc.stderr.read())` to see what the subprocess emitted. |
| `brew audit --strict` complains about deprecated `plist` block | Used wrong DSL | Confirm `service do ... end` syntax; no `plist do ... end`. |
| `brew services list` shows `error` immediately after `start` | Wrapper crashed | Run `project-brain-mcp --http` directly in a terminal to see the actual error. Likely a missing dependency or a Python import failure inside the venv. |
| Day-8 PR diff shows changes outside ChatGPT INSTALL section | Accidental edits to other sections | Revert hunks via `git checkout main -- INSTALL.md` then re-apply only ChatGPT changes. |
| `sse_client` from `mcp.client.sse` not importable in smoke test | Smoke test running in system Python that doesn't have `mcp` installed | The smoke test already handles this via `pip install --break-system-packages mcp pydantic anyio` in CI; locally use the same venv as pipx-editable. |

## Escalation triggers

Stop and surface to Tom if:

- FastMCP doesn't expose SSE transport at all in the installed `mcp` version, and bumping the version requires invasive changes (e.g., API breaks elsewhere). Escalation note should propose: (a) bump SDK version + fix breakage, or (b) fall back to `mcp-remote` bridge (the original day-8 plan).
- The SSE endpoint serves traffic from `curl` but day-9's ChatGPT connector reports it can't establish a session. **Don't push to PR** if this surfaces during local testing; escalate as a compatibility gap and propose falling back to `mcp-remote` bridge for v1.0.
- `brew audit --strict` rejects the `service` DSL with errors that can't be resolved by syntax tweaks.
- Port 8787 conflicts with another commonly-used local service that v1.0 users would hit (e.g., another MCP server's default port). Propose a different default port and update INSTALL.md.

Write the escalation to `docs/handoff/day-08-escalation.md` with the failure detail + decision required. Don't push to a PR until escalation is resolved.

## Notes for the next handoff (day-9)

Day-9 = **ChatGPT Desktop E2E demo** against the brew-installed `project-brain-mcp` SSE service. Concrete deliverables:

- Fresh-machine demo: `brew install project-brain-mcp`, `brew services start project-brain-mcp`, set `PROJECT_BRAIN_HOME` in shell profile, restart service, add custom connector in ChatGPT Plus (`http://localhost:8787/sse`), prompt round-trip ("list my threads" → "create a thread").
- `docs/demos/day-09-chatgpt-desktop.md` with transcript, screenshots, full sequence.
- compat-matrix ChatGPT Plus+ "First-session validated" flips from `pending (day-9)` to `yes (week 2, day-9 demo)`.
- **Critical**: if the demo fails because ChatGPT can't establish an MCP session with FastMCP's SSE server, escalate back to a day-8 hotfix. Two fix paths:
    1. Debug the SSE handshake; small wire-format adjustments.
    2. Fall back to shipping `mcp-remote` as a bridge formula for v1.0 ChatGPT; defer the native-SSE story to v1.0.1.
  Both paths are tractable within a 1-2 day hotfix window.

**Day-10** = Codex CLI E2E demo against the brew-installed `project-brain-mcp` stdio. compat-matrix Codex row flips from `pending (day-8)` to `yes`.

**Week 3 (days 11-14)** = polish + final v1.0.0 release:
- README rewrite.
- Final v1.0.0 tag (drops the `-rc.N` suffix).
- Tap formula bumps to `v1.0.0` final.
- Brew-install-and-daemon thread closure (open questions 1-5 resolved by the v1.0 release).
- Homebrew-core submission consideration (or defer to v1.1).
- v1.1 backlog refresh based on what days 9-10 surface.
