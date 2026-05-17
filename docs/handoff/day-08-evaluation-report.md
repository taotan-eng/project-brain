# Day-8 Evaluation Report

- Generated: 2026-05-17T04:30:00Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 2 day 3)
- Handoff: `docs/handoff/day-08-brew-bridge-daemon.md` (the filename predates the 2026-05-17 rewrite; content is the native-SSE plan)
- Predecessor: day-07 (merged to main via PR #7, commit `b79c2f2`)
- Week 2 day 3: ChatGPT support via native SSE transport in `project-brain-mcp` (replaces the originally-planned `mcp-remote` bridge daemon)

## Architecture note: native SSE chosen over mcp-remote bridge

Two paths were on the table for ChatGPT support:

- **Option 1 (original day-8 plan)**: a separate `project-brain-bridge` formula that depends on Node and runs `mcp-remote` as a launchd service. Battle-tested specifically against ChatGPT's custom-connector flow.
- **Option 2 (chosen)**: use FastMCP's built-in SSE transport. Same `project-brain-mcp` binary, new CLI flag, no new dependency.

This branch ships Option 2. The `mcp` Python package already in `pyproject.toml` exposes `FastMCP.run(transport="sse")` (and the lower-level `run_sse_async()` / `sse_app()`) — adding a `--http` flag to `__main__.py` lets the same binary serve stdio (the default; used by Claude Desktop, Codex CLI, Claude Code) or SSE (used by ChatGPT). No npm, no Node, no `project-brain-bridge` formula — the `Formula/project-brain-mcp.rb` from day-7 gains a `service do ... end` block and `brew services start project-brain-mcp` runs the SSE daemon on `127.0.0.1:8787`.

**Risk acknowledgment** (from the handoff): FastMCP's SSE transport hasn't been field-tested against ChatGPT's custom-connector flow as extensively as `mcp-remote` has. If day-9's E2E demo finds a compatibility gap, the documented fallback is to ship `mcp-remote` (Option 1) in v1.0.1 as a `project-brain-bridge` formula. v1.0 stdio paths are unaffected either way.

## Script adjustments from handoff spec

Four deviations from the handoff, transparently captured:

1. **`app.run(transport="sse", host=..., port=...)` does not accept `host`/`port` kwargs.** The handoff's reference code passed them as kwargs to `FastMCP.run()`; the installed `mcp==1.27.1` exposes only `(transport, mount_path)`. Configured `app.settings.host` and `app.settings.port` directly on the FastMCP instance before invoking `app.run(transport="sse")`. Net behavior matches the handoff intent; just a different attachment point for the config. Stdio path kept the existing `asyncio.run(app.run_stdio_async())` invocation rather than switching to the synchronous wrapper, so the day-7 stdio behavior is byte-identical.
2. **Local `brew install` was blocked by the same sandbox file-permission limit as day-7** (`/opt/homebrew/Library/Taps/homebrew/homebrew-core` is not writable in this environment, so `brew install` can't tap homebrew-core for its `python@3.12` dependency). `brew style --fix` and `brew audit --strict --formula ai-project-brain/project-brain/project-brain-mcp` (after re-tapping via symlink so brew sees the rc.6-bumped local copy) both pass with exit 0. Criterion 6 + 7 are validated by tap CI on `macos-latest`, which has homebrew-core pre-tapped. Documented in day-7's eval too; same constraint, same workaround.
3. **The smoke test's `_sse_roundtrip` invokes `sys.executable -m project_brain_mcp --http`**, not the `project-brain-mcp` PATH binary. This parallels the existing stdio path's `StdioServerParameters(command=sys.executable, args=["-m", "project_brain_mcp"], ...)` (line 180 of the smoke runner) so subprocess and parent share the same interpreter and editable-install resolution. The criterion-1 / criterion-3 PATH binary is separately exercised by the local verify snippet (Task 1) and by the tap CI's "Verify binary on PATH" + "Start service + probe SSE endpoint" steps.
4. **Tap-CI SSE probe needed a follow-up commit.** The first tap CI run on rc.6 ([run 25981872515](https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25981872515)) reached the new "Start service + probe SSE endpoint" step but reported `SSE endpoint did not come up within 5s` even though the brew service was healthy. Root cause: the probe used `curl -sSf --max-time 1` and relied on curl's exit code, but SSE keeps the connection open until the client disconnects, so curl times out (exit 28) on every probe even when the endpoint returned HTTP 200 with the initial event payload. The service log on that run confirmed `GET /sse HTTP/1.1" 200 OK` arrived as expected. Fixed by switching the probe to capture `%{http_code}` via `-w` and check that against `200`, swallowing curl's exit with `|| true`. Pushed as tap commit [`3070455`](https://github.com/ai-project-brain/homebrew-project-brain/commit/3070455); CI re-ran as [run 25982080638](https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25982080638) and went green.

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `--http` flag works | ✓ | Local `project-brain-mcp --http` binds 127.0.0.1:8787; `curl http://localhost:8787/sse` returned `200 text/event-stream; charset=utf-8` after a 4-poll bind delay. Service log shows `GET /sse HTTP/1.1" 200 OK`. SIGTERM cleans up the uvicorn process within 1s. |
| 2 | `PROJECT_BRAIN_SSE_PORT` honored | ✓ | `PROJECT_BRAIN_SSE_PORT=8800 project-brain-mcp --http` binds 8800; `curl` against 8800 returns 200, against 8787 returns connection-refused. `PROJECT_BRAIN_SSE_PORT=banana ...` exits with `FATAL: invalid PROJECT_BRAIN_SSE_PORT='banana' (...)` to stderr and exit code 2. |
| 3 | Default stdio unchanged | ✓ | `project-brain-mcp` (no flag) starts in stdio mode; smoke test's stdio roundtrip (15 categories, ≥17 tools, ≥14 prompts, 3 resources, all CRUD + error paths) prints `stdio roundtrip: PASSED`. Counts identical to day-7 baseline. `__main__.py`'s stdio branch still calls `asyncio.run(app.run_stdio_async())` — zero behavioral diff for stdio hosts. |
| 4 | SSE smoke test added + passes | ✓ | `scripts/smoke_mcp_roundtrip.py` adds `_sse_roundtrip()` + `_run_all()` wrapper. Local run prints `SSE roundtrip: 17 tools, 17 prompts` then `MCP SMOKE TEST PASSED (stdio + SSE)`. Tap CI's "Clone main repo + run smoke test" step verifies the same in the brew-installed environment. |
| 5 | v1.0.0-rc.6 tag + release | ✓ | `git tag v1.0.0-rc.6` on commit `9fb90b5`. `gh release view v1.0.0-rc.6` shows published release at https://github.com/ai-project-brain/project-brain/releases/tag/v1.0.0-rc.6. Tarball sha256 = `fcbb7c3f585297ff0d5f796083d9129224a351e8dce3462f41d939115edd23aa` (computed via `curl ... \| shasum -a 256`). Formula's `url` + `sha256` match. |
| 6 | Formula edits clean + service block valid | ✓ | `brew style --fix` clean (no offenses). `brew audit --strict --formula ai-project-brain/project-brain/project-brain-mcp` exit 0 (no warnings). Service block uses the modern DSL: `service do; run [opt_bin/"project-brain-mcp", "--http"]; keep_alive true; log_path var/"log/...log"; error_log_path var/"log/...error.log"; end`. No deprecated `plist do ... end`. |
| 7 | Service starts + SSE responds via brew | ✓ (tap CI) | Tap CI [run 25982080638](https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25982080638) step "Start service + probe SSE endpoint": `brew services start project-brain-mcp` → poll `%{http_code}` up to 5s → status 200 + `text/event-stream` → `SSE OK`. Cleanup step (always-run) calls `brew services stop`. Local validation blocked by sandbox file-permission limit (§ Script adjustments #2). The first CI iteration on the rc.6 formula commit ([run 25981872515](https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25981872515)) needed a follow-up probe fix — see § Script adjustments #4. |
| 8 | INSTALL.md + compat-matrix updates correct | ✓ | INSTALL.md `## ChatGPT Desktop config`: Step 1 reads `brew install ai-project-brain/project-brain/project-brain-mcp && brew services start project-brain-mcp`. No `npx`, no `mcp-remote`, no foreground-terminal step. Verify/stop/restart/port-override subsections present. Step 2 connector URL unchanged at `http://localhost:8787/sse`. Free-tier paragraph preserved. Diff is confined to `## ChatGPT Desktop config` (verified via `git diff origin/main..HEAD -- INSTALL.md` — only the ChatGPT hunk lands; Claude Desktop / Codex / Claude Code sections untouched). compat-matrix.md ChatGPT Plus+ row: Transport `HTTP/SSE` (no longer `via bridge`); Notes contains `brew install project-brain-mcp && brew services start project-brain-mcp`. "First-session validated" advanced to `pending (day-9)`. |

## Files changed (this branch vs main)

```
 INSTALL.md                            |  53 +++++++++++++----
 compat-matrix.md                      |   2 +-
 mcp/src/project_brain_mcp/__main__.py |  40 ++++++++++++-
 scripts/smoke_mcp_roundtrip.py        | 104 +++++++++++++++++++++++++++++++++-
 4 files changed, 183 insertions(+), 16 deletions(-)
```

Plus the eval report you're reading (`docs/handoff/day-08-evaluation-report.md`).

Tap repo changes (NOT in this PR — sibling repo `ai-project-brain/homebrew-project-brain`):

```
 Formula/project-brain-mcp.rb              | 13 ++--   (rc.5 → rc.6 + service block + desc bump)
 .github/workflows/brew-formula-build.yml  | 50 +++++  (service-start + SSE probe + cleanup + probe-fix)
```

## Commits (this branch)

```
102e6ec docs(compat): native SSE replaces mcp-remote bridge in ChatGPT row
51ac8bb docs(install): rewrite ChatGPT section for native SSE daemon
9fb90b5 test(mcp): extend smoke to exercise SSE transport
effd511 feat(mcp): add SSE transport via --http flag
```

(Plus the final `docs(handoff): stage day-8 plan + evaluation report (MERGE-READY)` commit landing this report.)

## Tap repo state

- URL: https://github.com/ai-project-brain/homebrew-project-brain
- Default branch: `main`
- Formula: `Formula/project-brain-mcp.rb` ships `project-brain-mcp v1.0.0-rc.6` with `service do ... end` block
- CI workflow: `.github/workflows/brew-formula-build.yml` builds + smoke-tests + starts service + probes SSE on `macos-latest` for every push.
- CI run for the final tap commit (`3070455`, probe-fix on top of rc.6 + SSE probe): https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25982080638
- Tap-repo commit SHAs:
  - `f7899ed feat(formula): bump to rc.6 + add service block for SSE daemon`
  - `4b28076 ci(tap): probe SSE endpoint after brew services start`
  - `3070455 ci(tap): probe SSE via %{http_code}, not curl exit code` (fixes the curl-on-SSE-times-out bug from § Script adjustments #4)

## Verdict

**MERGE-READY.**

All 8 criteria are green. The native-SSE path is end-to-end validated by tap CI on a fresh `macos-latest` runner: rc.6 formula installs cleanly, `brew services start project-brain-mcp` launches the SSE daemon under launchd, and `curl http://localhost:8787/sse` returns 200 + `text/event-stream`. The stdio default is byte-identical to day-7 — Claude Desktop / Codex / Claude Code users see zero behavioral change. INSTALL.md's ChatGPT section is rewritten to the `brew install + brew services start` pattern with no `npx mcp-remote` or foreground-terminal step. compat-matrix.md drops the "(via bridge)" qualifier and advances the demo target to day-9 (E2E ChatGPT connector add). Four deviations from the spec are documented in § Script adjustments; none alter user-visible install behavior. Ready for review and merge to `main`.

Day-9 will exercise the actual ChatGPT connector add against this binary. If FastMCP's SSE handshake turns out to be incompatible with ChatGPT's client, the documented fallback is to ship `mcp-remote` as a `project-brain-bridge` formula for v1.0.1; v1.0's stdio paths and the `--http` flag itself remain useful even in that fallback scenario.
