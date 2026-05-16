# Day 5 Handoff — Complex tools + INSTALL.md + Claude Desktop install demo

- **Audience**: Claude Code (or any agent operating on the project-brain repo)
- **Date authored**: 2026-05-13
- **Author**: Tom (taotan6@gmail.com) via planning session
- **Estimated effort**: 1-1.5 person-days
- **Status**: ready
- **Execution mode**: autonomous test-fix-retest loop; escalate only on judgment calls (see § Escalation)
- **Predecessor**: `day-04-mcp-tool-coverage.md` (status: done; PR merged to `main`)
- **Branch**: `day-05/install-and-complex-tools` (created at pre-flight)

## TL;DR

Close out week 1 with the three remaining complex tools and the actual end-user install path:

1. **3 complex tools**: `init_project_brain`, `promote_thread_to_tree` (with required `allow_domain` consent param), `materialize_context`. Tool count: 14 (day-4) → **17 (day-5)**.
2. **multi-agent debate** is **deliberately not a tool** — it's exposed only as a prompt (already auto-registered in day-4). Subagent spawning belongs to the MCP client's domain, not the server's. Documented decision in § Out of scope.
3. **`INSTALL.md`** at repo root with a Claude Desktop config snippet, `uvx project-brain-mcp` install command, and verification steps.
4. **Extended smoke test** covers the 3 new tools plus a deliberate consent-rejection assertion (omit `allow_domain` → `validation_error`).
5. **End-user demo evidence**: a manual install + first-thread roundtrip on Claude Desktop Pro, captured as `docs/demos/day-05-claude-desktop-install.md` (transcript or screenshot description; format flexible).

End of day-5 the MCP server is functionally complete for v1.0, and there's a verified install path a non-CC user can follow to get project-brain running on Claude Desktop. Week 1 done.

## Context

You are executing **day 5 of week 1 of the project-brain v1.0 3-week release plan**. This is the week-1 finale.

Read these for "why" decisions:

- **Plan artifact**: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 1 day 5).
- **Day-4 handoff + evaluation report** — establishes the 14-tool / 17-prompt / structured-error baseline that day-5 extends to 17 tools.
- **Round-01 patches P1, P5, P11** + the `promote-thread-to-tree` 5-round hardening from earlier work — the consent gate ("Forbidden / Only valid value source / `--allow-domain`") MUST remain intact when exposed via MCP.
- **Convention**: `docs/handoff/README.md` § Workflow + § PR-merge criteria + the canonical `_evaluation-report-template.md`.

Day-4 wrapped the everyday lifecycle tools and made prompts auto-discover. Day-5 picks up the four tools that don't fit the thin-wrapper pattern — except `multi_agent_debate`, which is reframed below as a prompt-only surface.

## Why `multi_agent_debate` is not a tool

Multi-agent debate spawns subagents that review an artifact in parallel, then runs a defender that issues per-claim verdicts. In Cowork that uses the host's Task tool. In MCP there's no equivalent — the MCP server is a stdio child process; it cannot spawn agent children of its own. The realistic shape is:

- The **prompt** `multi-agent-debate` (already registered in day-4's auto-discovery) tells the calling agent to spawn its own reviewer subagents using whatever facility its host provides (Cowork's Task tool, Claude Code's subagent mechanism, ChatGPT's nested-conversation pattern, etc.).
- The **Layer-1 scripts** under `scripts/` still produce the round directory, feedback brief, persona roster, etc.
- The orchestration glue between "spawn reviewer" and "write tryout.md" lives in the calling agent, not in the MCP server.

So `multi_agent_debate` is a prompt, not a tool. The user reading day-5 should not look for a tool by that name; they get the workflow by invoking the prompt and following its instructions, plus calling the simpler tools (`record_artifact`, `update_thread`) that the prompt body references.

This is an architectural decision worth committing to: **MCP tools wrap Layer-1 scripts that have a single deterministic invocation. Workflows that orchestrate sub-agents stay as prompts.** Future complex skills follow the same rule.

## Goal

By the end of this handoff:

1. **Three new tools** registered with Pydantic schemas:
    - `init_project_brain`: creates a new brain at a target directory; refuses if the target already has a brain unless `force=True`.
    - `promote_thread_to_tree`: promotes thread leaves into `tree/<domain>/`; **requires** `allow_domain` (no default — Pydantic enforces). The required-param IS the consent gate at the MCP boundary.
    - `materialize_context`: walks the soft_links graph for a thread or leaf and returns the resolved content as structured response data.
2. `tools.py` and `server.py` register all 17 tools (14 day-4 + 3 day-5).
3. `INSTALL.md` at repo root provides a copy-pasteable Claude Desktop MCP config snippet, the `uvx project-brain-mcp` install command, and three verification steps a user runs after install.
4. The smoke test extends to cover the 3 new tools and asserts that `promote_thread_to_tree` without `allow_domain` returns `error.code == "validation_error"` — the consent gate fires.
5. A short demo doc at `docs/demos/day-05-claude-desktop-install.md` captures an actual end-to-end install on Claude Desktop Pro (transcript, screenshots, or both). This is the only criterion that requires the human in the loop.
6. The evaluation report at `docs/handoff/day-05-evaluation-report.md` documents 8/8 merge criteria pass; the day-5 PR is open against `main` with that report as its body.

## PR-merge criteria

| # | Criterion | Programmatic check |
|---|---|---|
| 1 | 3 new complex tools wired (17 total) | `tools.py` defines `InitProjectBrainArgs`, `PromoteThreadToTreeArgs`, `MaterializeContextArgs`; `server.py` registers the matching `@app.tool` for each. Server `tools/list` returns ≥17 names. |
| 2 | `promote_thread_to_tree` consent gate intact | `PromoteThreadToTreeArgs` has `allow_domain: str` (no default — Pydantic-required). Smoke test asserts: omitting `allow_domain` → `error.code == "validation_error"`. Passing it succeeds. |
| 3 | `init_project_brain` safety guard | `init_project_brain` with a target dir that already has a `project-brain/CONVENTIONS.md` and `force=False` (default) returns `error.code == "script_error"` with a hint mentioning "existing brain". With `force=True` it proceeds. |
| 4 | `materialize_context` returns structured data | Smoke test invokes `materialize_context` on a thread with at least one soft_link; response.ok is True; response.data contains a `context` or equivalent field with content >0 bytes. |
| 5 | `INSTALL.md` present + structurally complete | `INSTALL.md` at repo root contains: (a) a `uvx project-brain-mcp` or `pipx install project-brain-mcp` install command; (b) a JSON code block with a `mcpServers` config snippet for Claude Desktop; (c) at least three verification steps the user runs after install. Verified by grep on the three section markers. |
| 6 | End-user demo evidence captured | `docs/demos/day-05-claude-desktop-install.md` exists with at minimum a short transcript or screenshot description showing: (a) the user pasted the config, (b) restarted Claude Desktop, (c) created a thread via the agent, (d) the brain on disk has the new thread. Format flexible. |
| 7 | Extended smoke test passes | `scripts/smoke_mcp_roundtrip.py` exits 0. Exercises ≥9 distinct tools (the 6 from day-4 + the 3 new). Includes the consent-gate assertion (criterion 2) and the init safety guard assertion (criterion 3). |
| 8 | No regression: validator green + test suite (modulo bash 3.2 baseline) + no Cowork refs + Conventional Commits + smoke-test naming respected | Validator `0 errors`; tests match day-4 baseline (4 PromoteLocalTests failures, no new); Cowork refs in `skills/` = 0; live `discover-threads` refs = 0; no new `scripts/test_*.py` files importing optional deps. |

Workflow:

- Working branch is `day-05/install-and-complex-tools` off `main`.
- Day-5 commits use Conventional Commits with scope (e.g. `feat(mcp): wire promote_thread_to_tree`, `docs: add INSTALL.md`).
- After MERGE-READY, branch is pushed; PR opened against `main` with `docs/handoff/day-05-evaluation-report.md` as body.

## Development loop

Standard. Each task: spec → execute → run validation → consult Common failure modes on fail → ~5 retries max → escalate.

**Sequencing note**: Tasks 1 and 5 can run in parallel (tools and INSTALL.md touch different files). Task 6 (demo) requires you, the agent, to coordinate with Tom for the manual step. Save it for last.

## Pre-flight checks

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Right repo
test -f CONVENTIONS.md -a -d skills/ -a -f README.md -a -d mcp/ \
  || { echo "FAIL: not in project-brain pack repo"; exit 1; }

# 2. gh CLI installed and authed
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 \
  || { echo "FAIL: gh missing or unauthed"; exit 1; }

# 3. Working tree clean
[ -z "$(git status --porcelain)" ] \
  || { echo "FAIL: uncommitted changes"; git status; exit 1; }

# 4. Day-4 must be merged to main. Accept either (a) the exact commit
#    subjects on main, or (b) a squash-merge PR title pattern.
git fetch origin main 2>&1 >/dev/null || true
MAIN_LOG=$(git log origin/main --oneline -30 2>/dev/null)
echo "$MAIN_LOG" | grep -qE "(expand to 14 tools|Day 04|day-04)" \
  || { echo "FAIL: day-4 not on origin/main (looked for commit subject or squashed PR title)"; exit 1; }
echo "$MAIN_LOG" | grep -qE "(scaffold project-brain-mcp|Day 03|day-03)" \
  || { echo "FAIL: day-3 not on origin/main (looked for commit subject or squashed PR title)"; exit 1; }

# 5. Branch setup
current=$(git branch --show-current)
if [ "$current" != "day-05/install-and-complex-tools" ]; then
  git checkout main
  git pull --ff-only 2>&1 | head -2 || true
  if git rev-parse --verify day-05/install-and-complex-tools >/dev/null 2>&1; then
    git checkout day-05/install-and-complex-tools
  else
    git checkout -b day-05/install-and-complex-tools
  fi
fi
test "$(git branch --show-current)" = "day-05/install-and-complex-tools" \
  || { echo "FAIL: not on day-05 branch"; exit 1; }

# 6. Validator green BEFORE we start
python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 \
  | tail -1 | grep -q "0 errors" \
  || { echo "FAIL: validator dirty"; exit 1; }

# 7. MCP package + day-4 smoke test pass
python3 -c "import project_brain_mcp; from project_brain_mcp.server import app" \
  || { echo "FAIL: project_brain_mcp not importable"; exit 1; }
python3 scripts/smoke_mcp_roundtrip.py 2>&1 | tail -1 | grep -q "MCP SMOKE TEST PASSED" \
  || { echo "FAIL: day-4 smoke test fails before day-5"; exit 1; }

# 8. Day-4 tool count is 14 (sanity)
N=$(python3 -c "
import asyncio
from project_brain_mcp.server import app
async def m(): print(len(await app.list_tools()))
asyncio.run(m())
" 2>/dev/null | tr -d ' ')
[ "$N" -ge 14 ] || { echo "FAIL: expected ≥14 day-4 tools, got $N"; exit 1; }

echo "ALL PRE-FLIGHT CHECKS PASSED — on branch day-05/install-and-complex-tools (day-4 baseline: $N tools)"
```

## Task 1 — Wire `init_project_brain`

### Spec

Thin wrapper around `scripts/init-brain.sh`. Special pre-validation: if the target dir already has `<target>/CONVENTIONS.md` (an existing brain marker), refuse with `script_error` unless `force=True`.

```python
class InitProjectBrainArgs(BaseModel):
    target: str = Field(description="Absolute path where the brain should be initialized")
    primary_project: str = Field(description="Alias for the new brain's primary project")
    owner: str | None = Field(default=None, description="Owner email (defaults to TODO@example.com if omitted)")
    force: bool = Field(default=False, description="If true, allow overwriting an existing brain at target")

async def init_project_brain_impl(args: InitProjectBrainArgs) -> dict:
    # Pre-flight: refuse if a brain already exists and force=False
    marker = Path(args.target) / "CONVENTIONS.md"
    if marker.exists() and not args.force:
        return err("script_error",
                   f"target {args.target} already has an existing brain (CONVENTIONS.md present)",
                   hint="set force=True to overwrite, or pick a different target directory")
    argv = [f"--target={args.target}", f"--primary-project={args.primary_project}"]
    if args.owner:
        argv.append(f"--owner={args.owner}")
    if args.force:
        argv.append("--force")
    return from_subprocess_result(run_script("init-brain.sh", argv))
```

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Args model + impl present
python3 - <<'PY'
from project_brain_mcp.tools import InitProjectBrainArgs, init_project_brain_impl
# Required fields enforced
try:
    InitProjectBrainArgs()
    raise AssertionError("InitProjectBrainArgs accepted missing required fields")
except Exception:
    pass
# Force is bool with default False
args = InitProjectBrainArgs(target="/tmp/x", primary_project="t")
assert args.force is False
print("  ✓ InitProjectBrainArgs validates required fields, force default False")
PY

# 2. Tool registered in server.py
grep -q '@app.tool(name="init_project_brain"' mcp/src/project_brain_mcp/server.py \
  || { echo "FAIL: init_project_brain not registered"; exit 1; }

# 3. Safety guard fires on existing brain (test in-process)
python3 - <<'PY'
import asyncio, tempfile
from pathlib import Path
from project_brain_mcp.tools import InitProjectBrainArgs, init_project_brain_impl

async def main():
    with tempfile.TemporaryDirectory() as tmp:
        # Plant an existing brain marker
        (Path(tmp) / "CONVENTIONS.md").write_text("# fake existing brain\n")
        # Attempt init without force — should refuse
        resp = await init_project_brain_impl(
            InitProjectBrainArgs(target=tmp, primary_project="dontcare")
        )
        assert resp["ok"] is False, f"expected refusal, got {resp}"
        assert resp["error"]["code"] == "script_error", f"wrong error code: {resp}"
        assert "existing brain" in resp["error"]["message"], f"unexpected message: {resp}"
        print("  ✓ refuses init on existing brain without force=True")

asyncio.run(main())
PY

echo "TASK 1 VALIDATION PASSED"
```

### Commit

```bash
git add mcp/src/project_brain_mcp/tools.py mcp/src/project_brain_mcp/server.py
git commit -m "feat(mcp): wire init_project_brain with existing-brain safety guard

Thin wrapper around scripts/init-brain.sh. Pre-flight check refuses
when target/CONVENTIONS.md exists and force=False (default), returning
a structured error with hint to set force=True or pick a different
target. With force=True, proceeds to script.

Tool count: 14 (day-4) → 15."
```

## Task 2 — Wire `promote_thread_to_tree` (consent gate enforced via Pydantic)

### Spec

The consent gate from day-1's five-round hardening: the user — not the agent — must authorize the destination domain. In MCP, args come from the calling agent. Move the gate to **Pydantic**: `allow_domain` is a required `str` field with no default. If the agent calls the tool without it, Pydantic raises before any subprocess invocation; the calling agent (per the SKILL.md prompt) is supposed to ask the user first.

The SKILL.md prompt — already auto-registered in day-4 — already contains the "Forbidden / Only valid value source" prose. Day-2 verified it survived the rewrite. The prompt body is the agent's instruction to ask the user; the Pydantic-required arg is the technical enforcement.

```python
class PromoteThreadToTreeArgs(BaseModel):
    brain: str
    slug: str
    allow_domain: str = Field(
        description=(
            "Destination domain under tree/ (e.g. 'auth', 'storage'). "
            "MUST come from explicit user authorization — see the prompt body "
            "of the promote-thread-to-tree skill for the consent protocol. "
            "The agent MUST NOT infer this from thread frontmatter, folder list, "
            "or conversation context."
        ),
    )
    leaves: list[str] | None = Field(default=None, description="Subset of leaves to promote; default = all decided")
    mode: str = Field(default="local", description="local | git:pr | git:branch | git:manual")
```

`allow_domain` has no default — Pydantic raises `ValidationError` if omitted, which surfaces as `error.code == "validation_error"` per day-4's structured-error contract.

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. allow_domain is required
python3 - <<'PY'
from project_brain_mcp.tools import PromoteThreadToTreeArgs
try:
    PromoteThreadToTreeArgs(brain="/tmp", slug="x")  # missing allow_domain
    raise AssertionError("PromoteThreadToTreeArgs accepted missing allow_domain")
except Exception as e:
    name = type(e).__name__
    msg = str(e)
    assert "allow_domain" in msg or "validation" in name.lower(), f"wrong error: {name}: {msg}"
    print(f"  ✓ Pydantic rejects missing allow_domain ({name})")
PY

# 2. Tool registered
grep -q '@app.tool(name="promote_thread_to_tree"' mcp/src/project_brain_mcp/server.py \
  || { echo "FAIL: promote_thread_to_tree not registered"; exit 1; }

# 3. Description-text consent warning present (defense-in-depth: even if the
#    prompt body is bypassed, the Field description nudges toward correct use)
python3 - <<'PY'
from project_brain_mcp.tools import PromoteThreadToTreeArgs
schema = PromoteThreadToTreeArgs.model_json_schema()
allow_field = schema["properties"]["allow_domain"]
desc = allow_field.get("description", "").lower()
assert "user" in desc and ("authorization" in desc or "consent" in desc or "must come from" in desc), \
    f"allow_domain description doesn't mention user-consent semantics: {desc!r}"
print("  ✓ allow_domain Field description includes consent-semantics warning")
PY

# 4. Companion prompt (auto-registered day-4) still serves the SKILL.md body
python3 - <<'PY'
import asyncio
from project_brain_mcp.server import app
async def main():
    prompts = await app.list_prompts()
    names = {p.name for p in prompts}
    assert "promote-thread-to-tree" in names, "promote-thread-to-tree prompt missing"
    print("  ✓ promote-thread-to-tree prompt still auto-registered")
asyncio.run(main())
PY

echo "TASK 2 VALIDATION PASSED"
```

### Commit

```bash
git add mcp/src/project_brain_mcp/tools.py mcp/src/project_brain_mcp/server.py
git commit -m "feat(mcp): wire promote_thread_to_tree with required allow_domain consent

The consent gate from day-1's five-round hardening is now enforced at
the MCP boundary via Pydantic: allow_domain is a required str field
with no default. Omitting it returns error.code='validation_error'
before any subprocess invocation.

The Field description explicitly warns the agent that allow_domain
must come from explicit user authorization — defense in depth alongside
the prompt body (auto-registered day-4) which carries the full
'Forbidden / Only valid value source' protocol.

Tool count: 15 → 16."
```

## Task 3 — Wire `materialize_context`

### Spec

Walks the `soft_links` graph for a thread or leaf and returns the resolved content. Pure read; no state mutation.

```python
class MaterializeContextArgs(BaseModel):
    brain: str
    artifact: str = Field(description="Path to the artifact relative to brain (thread, leaf, or NODE.md)")
    consumer: str = Field(default="reviewer", description="reviewer | author | reader — affects role-based filtering")
    roles: list[str] = Field(default_factory=lambda: ["spec", "prior-decision"])
    persist: bool = Field(default=False, description="Persist into artifact dir for audit; default ephemeral scratch")
    detect_stale: bool = Field(default=False, description="Walk refs without materializing; report broken/drifted")

async def materialize_context_impl(args: MaterializeContextArgs) -> dict:
    argv = [
        f"--brain={args.brain}",
        f"--artifact={args.artifact}",
        f"--consumer={args.consumer}",
        f"--roles={','.join(args.roles)}",
    ]
    if args.persist:
        argv.append("--persist")
    if args.detect_stale:
        argv.append("--detect-stale")
    return from_subprocess_result(run_script("materialize-context.sh", argv))
```

If `scripts/materialize-context.sh` doesn't exist (the skill may be implemented inline in SKILL.md per day-4's audit caveat), surface in the execution log and skip — but flag prominently so the user can decide whether to write the wrapper or defer the tool to v1.1.

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Script exists (or surface the gap)
test -f scripts/materialize-context.sh \
  || { echo "WARNING: scripts/materialize-context.sh missing; document in execution log and skip tool — or escalate"; exit 1; }

# 2. Args model + tool registered
python3 - <<'PY'
from project_brain_mcp.tools import MaterializeContextArgs, materialize_context_impl
args = MaterializeContextArgs(brain="/tmp", artifact="threads/foo/thread.md")
assert args.consumer == "reviewer"
assert args.roles == ["spec", "prior-decision"]
print("  ✓ MaterializeContextArgs validates with sensible defaults")
PY
grep -q '@app.tool(name="materialize_context"' mcp/src/project_brain_mcp/server.py \
  || { echo "FAIL: materialize_context not registered"; exit 1; }

# 3. Tool count is 17
python3 - <<'PY'
import asyncio
from project_brain_mcp.server import app
async def main():
    n = len(await app.list_tools())
    assert n >= 17, f"expected ≥17 tools, got {n}"
    print(f"  ✓ {n} tools registered total")
asyncio.run(main())
PY

echo "TASK 3 VALIDATION PASSED"
```

### Commit

```bash
git add mcp/src/project_brain_mcp/tools.py mcp/src/project_brain_mcp/server.py
git commit -m "feat(mcp): wire materialize_context for soft_links graph resolution

Thin wrapper around scripts/materialize-context.sh. Takes an artifact
path, walks the soft_links graph per CONVENTIONS § 5.1, returns resolved
content as structured response. Defaults: consumer=reviewer,
roles=[spec, prior-decision], persist=False, detect_stale=False.

Tool count: 16 → 17. v1 MCP tool surface complete."
```

## Task 4 — `INSTALL.md`

### Spec

A new file `INSTALL.md` at the repo root. Three required sections (programmatically checked):

1. **`## Install`** — the canonical install command. Lead with `uvx project-brain-mcp` because it's the one-command-no-venv path. Mention `pipx install project-brain-mcp` and `pip install --user project-brain-mcp` as alternatives.

2. **`## Claude Desktop config`** — a JSON code block with the `mcpServers` snippet. Example:

    ```json
    {
      "mcpServers": {
        "project-brain": {
          "command": "uvx",
          "args": ["project-brain-mcp"],
          "env": {
            "PROJECT_BRAIN_HOME": "/absolute/path/to/your/brain"
          }
        }
      }
    }
    ```

    Plus the exact config-file path per OS (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, equivalents for Windows / Linux).

3. **`## Verify`** — at least three programmatic steps the user runs after install + restart:
    - In Claude Desktop, ask the agent something like "list my threads" — confirm the agent calls `list_threads`.
    - Ask the agent to "create a thread called Hello World" — confirm it lands on disk under `$PROJECT_BRAIN_HOME/threads/`.
    - Run `python3 -c "import project_brain_mcp; print(project_brain_mcp.__version__)"` — confirm import.

Plus an explicit note about tier support: Pro and Free both work for the config-edit path; Max gets the Cowork marketplace one-click (later).

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

test -f INSTALL.md || { echo "FAIL: INSTALL.md missing"; exit 1; }

# 1. Has the three required sections
for section in "## Install" "## Claude Desktop config" "## Verify"; do
  command grep -q "^${section}" INSTALL.md \
    || { echo "FAIL: INSTALL.md missing section: ${section}"; exit 1; }
done

# 2. Mentions uvx install command
command grep -q "uvx project-brain-mcp" INSTALL.md \
  || { echo "FAIL: INSTALL.md missing 'uvx project-brain-mcp' install command"; exit 1; }

# 3. Has a JSON config code block with mcpServers
command grep -q '"mcpServers"' INSTALL.md \
  && command grep -q '"project-brain"' INSTALL.md \
  || { echo "FAIL: INSTALL.md missing mcpServers JSON snippet"; exit 1; }

# 4. Mentions the config file path per OS (at least the macOS one)
command grep -q "claude_desktop_config.json" INSTALL.md \
  || { echo "FAIL: INSTALL.md missing Claude Desktop config file path"; exit 1; }

# 5. Mentions PROJECT_BRAIN_HOME env var (so the server knows where to operate)
command grep -q "PROJECT_BRAIN_HOME" INSTALL.md \
  || { echo "FAIL: INSTALL.md missing PROJECT_BRAIN_HOME env-var documentation"; exit 1; }

# 6. Has at least three verify steps (count list items under ## Verify)
N_STEPS=$(awk '/^## Verify/{f=1;next} /^## /{f=0} f && /^[0-9*-]/' INSTALL.md | wc -l | tr -d ' ')
[ "$N_STEPS" -ge 3 ] \
  || { echo "FAIL: INSTALL.md ## Verify has only $N_STEPS steps (need ≥3)"; exit 1; }

echo "TASK 4 VALIDATION PASSED"
```

### Commit

```bash
git add INSTALL.md
git commit -m "docs: add INSTALL.md with Claude Desktop MCP config + verification steps

User-facing install guide. Three required sections: Install (uvx command),
Claude Desktop config (mcpServers JSON snippet + per-OS config file path),
Verify (three programmatic post-install checks).

Documents PROJECT_BRAIN_HOME env var as the way to tell the MCP server
where the brain lives. Mentions pipx and pip as alternatives to uvx
for users without uv installed."
```

## Task 5 — Extended smoke test

### Spec

Extend `scripts/smoke_mcp_roundtrip.py` to cover the 3 new tools. Same stdio+ClientSession pattern. New assertions:

1. `tools/list` returns ≥17 names; confirm `init_project_brain`, `promote_thread_to_tree`, `materialize_context` are present.
2. `init_project_brain` on a scratch empty dir → succeeds; new CONVENTIONS.md exists at the target.
3. `init_project_brain` on the same dir again, `force=False` → `error.code == "script_error"` with "existing brain" in the message.
4. `promote_thread_to_tree` without `allow_domain` argument → `error.code == "validation_error"`.
5. `materialize_context` on a thread that has at least one soft_link → `ok=True`, response.data has content.
6. After all of the above, run `verify_tree` on the test brain → 0 errors.

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# Smoke test must pass
python3 scripts/smoke_mcp_roundtrip.py 2>&1 | tail -1 | grep -q "MCP SMOKE TEST PASSED" \
  || { echo "FAIL: extended smoke test did not pass"; exit 1; }

# At least 9 distinct tools exercised
N=$(grep -oE 'call_tool\("[a-z_]+"' scripts/smoke_mcp_roundtrip.py | sort -u | wc -l | tr -d ' ')
[ "$N" -ge 9 ] || { echo "FAIL: smoke test exercises only $N distinct tools (need ≥9)"; exit 1; }

# Consent-gate assertion present
grep -q "allow_domain.*validation_error\|validation_error.*allow_domain\|promote_thread_to_tree" scripts/smoke_mcp_roundtrip.py \
  || { echo "FAIL: smoke test missing consent-gate assertion"; exit 1; }

# Init safety-guard assertion present
grep -q "existing brain\|init_project_brain.*force\|force.*init_project_brain" scripts/smoke_mcp_roundtrip.py \
  || { echo "FAIL: smoke test missing init safety-guard assertion"; exit 1; }

echo "TASK 5 VALIDATION PASSED ($N distinct tools exercised)"
```

### Commit

```bash
git add scripts/smoke_mcp_roundtrip.py
git commit -m "test(mcp): extend smoke test to cover 3 day-5 complex tools

New assertions: init_project_brain happy path + force-guard refusal;
promote_thread_to_tree consent-gate firing (omit allow_domain →
validation_error); materialize_context happy path on a thread with
soft_links.

Total distinct tools exercised: 9+."
```

## Task 6 — End-user install demo on Claude Desktop

### Spec

A manual step that requires Tom on a real Claude Desktop install. The agent's job is to **prepare the demo doc skeleton** at `docs/demos/day-05-claude-desktop-install.md` and **ask Tom to run the demo**. Once Tom completes the demo, the doc is filled in with whatever evidence form makes sense (transcript, screenshots, or short prose description).

The demo script:

1. On the host, paste the `mcpServers` config from `INSTALL.md` into Claude Desktop's config file.
2. Set `PROJECT_BRAIN_HOME` env var in the config to point at a real brain dir (e.g., `/Users/ttan/workspace/Project-Brain/project-brain`).
3. Quit and re-launch Claude Desktop.
4. In a new chat, say: "Using project-brain, list my threads." Confirm the agent calls `list_threads` and returns the thread list.
5. Say: "Create a new thread called 'mcp demo' with purpose 'Day-5 install verification.'" Confirm the agent calls `new_thread` and the thread directory appears at `$PROJECT_BRAIN_HOME/threads/mcp-demo/`.
6. Capture: the chat transcript (or screenshot), the resulting directory listing, and any errors observed.

The skeleton doc has placeholders that Tom fills in. The agent commits the skeleton; Tom commits the filled-in version (or asks the agent to commit on Tom's behalf after pasting the content).

### Steps + Validation

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain
mkdir -p docs/demos

# 1. Create the skeleton if it doesn't exist
test -f docs/demos/day-05-claude-desktop-install.md || cat > docs/demos/day-05-claude-desktop-install.md <<'MD'
# Day-5 Claude Desktop Install Demo

- Date:
- Tester: Tom (taotan6@gmail.com)
- Claude Desktop version:
- macOS / OS version:
- MCP SDK version (`pip show project-brain-mcp`):

## Steps performed

1. Pasted the `mcpServers` config from `INSTALL.md` § "Claude Desktop config" into `~/Library/Application Support/Claude/claude_desktop_config.json`.
2. Set `PROJECT_BRAIN_HOME` in the config to: `<path>`.
3. Quit Claude Desktop and re-launched.
4. Opened a new chat and prompted: "Using project-brain, list my threads."
5. Prompted: "Create a new thread called 'mcp demo' with purpose 'Day-5 install verification.'"

## Evidence

### Step 4 — list_threads call

(Transcript or screenshot description here.)

### Step 5 — new_thread call

(Transcript or screenshot description here. Confirm: agent called `new_thread`, brain on disk now has `threads/mcp-demo/`.)

### After-state directory listing

```
$ ls $PROJECT_BRAIN_HOME/threads/mcp-demo/
(paste output here)
```

## Issues observed

(If any.)

## Verdict

(MERGE-READY-aligned: did the agent successfully use the MCP server end-to-end?)
MD

# 2. Validation: file exists with structural markers
test -f docs/demos/day-05-claude-desktop-install.md \
  || { echo "FAIL: demo skeleton missing"; exit 1; }
grep -q "^## Steps performed" docs/demos/day-05-claude-desktop-install.md \
  || { echo "FAIL: demo missing 'Steps performed' section"; exit 1; }
grep -q "^## Evidence" docs/demos/day-05-claude-desktop-install.md \
  || { echo "FAIL: demo missing 'Evidence' section"; exit 1; }
grep -q "^## Verdict" docs/demos/day-05-claude-desktop-install.md \
  || { echo "FAIL: demo missing 'Verdict' section"; exit 1; }

# 3. Check if Tom has filled in evidence (non-empty Evidence subsections)
# This is a soft check — if it's still empty, surface in the execution log
# and ask Tom before the End-of-day evaluation.
EVIDENCE=$(awk '/^### Step 4/{f=1} /^### Step 5/||/^## Issues/{f=0} f' docs/demos/day-05-claude-desktop-install.md | grep -v "^### Step 4\|^(Transcript or screenshot\|^$" | wc -l | tr -d ' ')
if [ "$EVIDENCE" = "0" ]; then
  echo "  ⚠ Step-4 evidence not yet filled in. Ask Tom to run the demo and paste evidence."
else
  echo "  ✓ Demo evidence captured ($EVIDENCE non-placeholder lines under Step 4)"
fi

echo "TASK 6 SKELETON IN PLACE"
```

After Tom fills in the demo evidence, commit it:

```bash
git add docs/demos/day-05-claude-desktop-install.md
git commit -m "docs(demo): day-5 Claude Desktop install verification (transcript)

Manual demo on Claude Desktop Pro: pasted mcpServers config, restarted
app, exercised list_threads + new_thread via natural-language prompts.
Confirmed end-to-end MCP roundtrip works for an end user; the brain on
disk has the new thread."
```

## Common failure modes and fixes

### Task 1 (init_project_brain)

| Symptom | Fix |
|---|---|
| `scripts/init-brain.sh` exits non-zero with "primary_project required" | The Pydantic model marks `primary_project` as required; ensure the impl includes it in argv. |
| Safety guard fires on a target that doesn't have a brain | The marker check uses `CONVENTIONS.md` — a target that has an unrelated `CONVENTIONS.md` would trip it. Make the marker check more specific: also require a `config.yaml` or `thread-index.md` next to it. |

### Task 2 (promote_thread_to_tree)

| Symptom | Fix |
|---|---|
| `allow_domain` description gets stripped by FastMCP before reaching the tool schema | Some MCP SDK versions strip rich descriptions. Use a shorter description as a fallback; keep the long one in a code comment. |
| Pydantic accepts empty string for `allow_domain` | Add `min_length=1` to the Field: `allow_domain: str = Field(..., min_length=1, description=...)`. Empty string is not user authorization. |

### Task 3 (materialize_context)

| Symptom | Fix |
|---|---|
| `scripts/materialize-context.sh` missing | Surface in execution log. Two options: (a) write a thin wrapper script that shells the Python materializer if it exists, or (b) defer the tool to v1.1 and document the absence in the eval report. Don't fabricate a script. |

### Task 4 (INSTALL.md)

| Symptom | Fix |
|---|---|
| Validation grep on "## Install" fails because the heading is "# Install" or "### Install" | Use the exact `## Install` (H2) heading — that's what the grep checks. |
| JSON snippet has invalid syntax | Run it through `python3 -c "import json; json.load(open('/dev/stdin'))"` to verify. |

### Task 5 (smoke test)

| Symptom | Fix |
|---|---|
| Smoke test passes locally but assertion 4 (consent-gate) misses | FastMCP may eat the Pydantic error before it reaches the response. Check the response shape; if Pydantic errors bubble up as `isError=True` instead of `error.code='validation_error'`, accept either pattern in the assertion. |
| `init_project_brain` happy-path fails because the scratch dir already has files from a previous test run | Use a fresh `tempfile.TemporaryDirectory` per assertion. |

### Task 6 (demo)

| Symptom | Fix |
|---|---|
| Tom hasn't filled in the evidence yet | Surface in execution log and pause before End-of-day evaluation. The demo is the human-in-the-loop gate; without evidence, criterion 6 fails. Wait for Tom. |
| Tom reports the agent didn't call the right tool | Investigate: was the MCP server actually loaded? Was `PROJECT_BRAIN_HOME` set? Did the agent's prompt context know about the project-brain tools? May require iterating on the prompt examples in INSTALL.md. |

### Cross-cutting

| Symptom | Fix |
|---|---|
| Pre-flight check 4 (day-4 on main) fails — looks like a squash-merge issue same as day-4 | The pre-flight already accepts BOTH the commit subject AND a "Day NN / day-NN" pattern in the PR title — this should match a squashed merge. If neither matches, check `git log origin/main` and update the check pattern in the eval script. |
| FUSE `.git/HEAD.lock` errors on commit | Standard sandbox remediation; `rm -f .git/HEAD.lock .git/index.lock` from host. |

## End-of-day evaluation

```bash
set +e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

REPORT=docs/handoff/day-05-evaluation-report.md
PASS=1
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
declare -a ROWS=()

# Criterion 1 — 17 tools
N_TOOLS=$(python3 -c "
import asyncio
from project_brain_mcp.server import app
async def m(): print(len(await app.list_tools()))
asyncio.run(m())
" 2>/dev/null | tr -d ' ')
if [ "$N_TOOLS" -ge 17 ]; then
  ROWS+=("| 1 | 3 new complex tools wired (17 total) | ✓ | ${N_TOOLS} tools registered |")
else
  ROWS+=("| 1 | 3 new complex tools wired | ✗ | only ${N_TOOLS} tools registered |")
  PASS=0
fi

# Criterion 2 — consent gate
CONSENT_OK=1
python3 - <<'PY' >/dev/null 2>&1 || CONSENT_OK=0
from project_brain_mcp.tools import PromoteThreadToTreeArgs
try:
    PromoteThreadToTreeArgs(brain="/tmp", slug="x")
    raise SystemExit(1)
except Exception:
    pass
PY
if [ "$CONSENT_OK" = "1" ]; then
  ROWS+=("| 2 | promote_thread_to_tree consent gate intact | ✓ | Pydantic rejects missing allow_domain |")
else
  ROWS+=("| 2 | consent gate | ✗ | allow_domain not enforced as required |")
  PASS=0
fi

# Criterion 3 — init safety guard (in-process check)
INIT_OK=1
python3 - <<'PY' >/dev/null 2>&1 || INIT_OK=0
import asyncio, tempfile
from pathlib import Path
from project_brain_mcp.tools import InitProjectBrainArgs, init_project_brain_impl
async def main():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "CONVENTIONS.md").write_text("# fake\n")
        resp = await init_project_brain_impl(InitProjectBrainArgs(target=tmp, primary_project="x"))
        assert resp["ok"] is False
        assert resp["error"]["code"] == "script_error"
asyncio.run(main())
PY
if [ "$INIT_OK" = "1" ]; then
  ROWS+=("| 3 | init_project_brain safety guard | ✓ | refuses existing brain unless force=True |")
else
  ROWS+=("| 3 | init safety guard | ✗ | guard didn't fire as expected |")
  PASS=0
fi

# Criterion 4 — materialize_context structural
MAT_OK=1
python3 -c "from project_brain_mcp.tools import MaterializeContextArgs, materialize_context_impl" 2>/dev/null || MAT_OK=0
if [ "$MAT_OK" = "1" ]; then
  ROWS+=("| 4 | materialize_context wired | ✓ | Args model + impl importable; smoke test exercises it |")
else
  ROWS+=("| 4 | materialize_context | ✗ | tool not wired |")
  PASS=0
fi

# Criterion 5 — INSTALL.md
INSTALL_OK=1
for sec in "## Install" "## Claude Desktop config" "## Verify"; do
  command grep -q "^${sec}" INSTALL.md 2>/dev/null || INSTALL_OK=0
done
command grep -q '"mcpServers"' INSTALL.md 2>/dev/null || INSTALL_OK=0
command grep -q "uvx project-brain-mcp" INSTALL.md 2>/dev/null || INSTALL_OK=0
command grep -q "PROJECT_BRAIN_HOME" INSTALL.md 2>/dev/null || INSTALL_OK=0
if [ "$INSTALL_OK" = "1" ]; then
  ROWS+=("| 5 | INSTALL.md present + structurally complete | ✓ | 3 sections, mcpServers JSON, uvx + PROJECT_BRAIN_HOME present |")
else
  ROWS+=("| 5 | INSTALL.md | ✗ | missing required sections or content |")
  PASS=0
fi

# Criterion 6 — demo evidence (soft check — passes if file exists with all 3 sections, even with placeholder evidence)
DEMO_OK=1
DEMO=docs/demos/day-05-claude-desktop-install.md
test -f "$DEMO" || DEMO_OK=0
command grep -q "^## Steps performed" "$DEMO" 2>/dev/null || DEMO_OK=0
command grep -q "^## Evidence" "$DEMO" 2>/dev/null || DEMO_OK=0
command grep -q "^## Verdict" "$DEMO" 2>/dev/null || DEMO_OK=0
# Soft check: warn if evidence is still placeholder
PLACEHOLDER=$(command grep -c "Transcript or screenshot description here" "$DEMO" 2>/dev/null || echo 0)
if [ "$DEMO_OK" = "1" ]; then
  if [ "$PLACEHOLDER" -gt 0 ]; then
    ROWS+=("| 6 | Demo evidence captured | ⚠ | skeleton in place, but ${PLACEHOLDER} placeholder block(s) still un-filled; ask Tom to capture real evidence before merge |")
    PASS=0   # placeholder evidence is NOT MERGE-READY
  else
    ROWS+=("| 6 | Demo evidence captured | ✓ | non-placeholder evidence under Steps + Evidence + Verdict |")
  fi
else
  ROWS+=("| 6 | Demo evidence captured | ✗ | demo file missing or incomplete sections |")
  PASS=0
fi

# Criterion 7 — extended smoke
SMOKE_OK=1
python3 scripts/smoke_mcp_roundtrip.py > /tmp/mcp-smoke-eval5.log 2>&1 || SMOKE_OK=0
command tail -1 /tmp/mcp-smoke-eval5.log | command grep -q "MCP SMOKE TEST PASSED" || SMOKE_OK=0
N_DISTINCT=$(command grep -oE 'call_tool\("[a-z_]+"' scripts/smoke_mcp_roundtrip.py 2>/dev/null | sort -u | wc -l | tr -d ' ')
if [ "$SMOKE_OK" = "1" ] && [ "$N_DISTINCT" -ge 9 ]; then
  ROWS+=("| 7 | Extended smoke test passes (≥9 tools + consent + init guards) | ✓ | ${N_DISTINCT} distinct tools exercised |")
else
  ROWS+=("| 7 | Extended smoke test | ✗ | passed=${SMOKE_OK}, distinct tools=${N_DISTINCT} |")
  PASS=0
fi

# Criterion 8 — no regression
VTOUT=$(python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 | command tail -1)
TESTS_OUT=$(python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | command tail -1)
COWORK=$(git grep -E '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' skills/ 2>/dev/null | wc -l | tr -d ' ')
OLD_NAME=$(git grep "discover-threads" 2>/dev/null | command grep -v "^CHANGELOG\.md\|^\.git\|^docs/handoff/" | wc -l | tr -d ' ')
BAD_TEST=$(ls scripts/test_*.py 2>/dev/null | command grep -v "test_verify_tree.py" | wc -l | tr -d ' ')
REGRESSION_OK=1
echo "$VTOUT" | command grep -q "0 errors" || REGRESSION_OK=0
[ "$COWORK" = "0" ] || REGRESSION_OK=0
[ "$OLD_NAME" = "0" ] || REGRESSION_OK=0
[ "$BAD_TEST" = "0" ] || REGRESSION_OK=0
TESTS_PASS=1
if echo "$TESTS_OUT" | command grep -q "^OK"; then :;
elif echo "$TESTS_OUT" | command grep -qE "FAILED \(failures=4\)"; then :;
else TESTS_PASS=0; fi
[ "$TESTS_PASS" = "1" ] || REGRESSION_OK=0
if [ "$REGRESSION_OK" = "1" ]; then
  ROWS+=("| 8 | No regression | ✓ | validator: ${VTOUT}; tests: ${TESTS_OUT}; cowork=0, discover-threads=0, bad-test-pattern=0 |")
else
  ROWS+=("| 8 | No regression | ✗ | validator=${VTOUT}; tests=${TESTS_OUT}; cowork=${COWORK}; old-name=${OLD_NAME}; bad-test=${BAD_TEST} |")
  PASS=0
fi

# Build the report
{
  echo "# Day-5 Evaluation Report"
  echo
  echo "- Generated: ${TIMESTAMP}"
  echo "- Plan reference: \`project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md\` § 4 (week 1 day 5)"
  echo "- Handoff: \`docs/handoff/day-05-complex-tools-and-install.md\`"
  echo "- Predecessor: day-04 (merged to main)"
  echo "- Week 1 finale: this evaluation closes out week 1 of v1.0"
  echo
  echo "## Merge criteria"
  echo
  echo "| # | Criterion | Status | Evidence |"
  echo "|---|---|---|---|"
  for row in "${ROWS[@]}"; do echo "$row"; done
  echo
  echo "## Files changed (this branch vs main)"
  echo
  echo '```'
  (git diff --stat main..HEAD 2>/dev/null || git diff --stat HEAD~8..HEAD) | sed 's/^/  /'
  echo '```'
  echo
  echo "## Commits (this branch)"
  echo
  echo '```'
  git log --oneline main..HEAD 2>/dev/null | sed 's/^/  /' || git log --oneline -10 | sed 's/^/  /'
  echo '```'
  echo
  if [ "$PASS" = "1" ]; then
    echo "## Verdict: **MERGE-READY**"
    echo
    echo "All eight criteria pass. Day-5 work is ready to merge via the day-05/install-and-complex-tools feature branch."
    echo
    echo "**Week 1 status: complete.** v1.0 MCP server has 17 tools, 17 prompts, 3 resources, structured errors, an end-user install path, and a verified Claude Desktop demo. Week 2 (ChatGPT + Codex MCP config snippets) and week 3 (eval suite + docs site + release) follow."
  else
    FAILED=$(printf '%s\n' "${ROWS[@]}" | command grep -E "✗|⚠" | awk -F'|' '{print $2}' | tr -d ' ')
    echo "## Verdict: **NOT-READY**"
    echo
    echo "Failing/incomplete criteria: ${FAILED}. See merge-criteria table above for evidence."
  fi
} > "$REPORT"

cat "$REPORT"
echo
if [ "$PASS" = "1" ]; then
  echo "✓ DAY-5 EVALUATION: MERGE-READY — report at $REPORT"
  exit 0
else
  echo "✗ DAY-5 EVALUATION: NOT-READY — report at $REPORT"
  exit 1
fi
```

## Exit gate

After the evaluation exits MERGE-READY:

1. Commit the evaluation report:
    ```bash
    git add docs/handoff/day-05-evaluation-report.md
    git commit -m "docs(handoff): day-5 evaluation report — MERGE-READY"
    ```
2. Update `Status:` → `done`.
3. Append `## Execution log` entry: wall-clock time, deviations, **closing thoughts on week 1**, anything week 2 should know.
4. Commit handoff-doc updates:
    ```bash
    git add docs/handoff/day-05-complex-tools-and-install.md
    git commit -m "docs(handoff): day-5 done — week 1 closed"
    ```
5. Push:
    ```bash
    git push -u origin day-05/install-and-complex-tools
    ```
6. Open the PR:
    ```bash
    gh pr create \
      --base main \
      --head day-05/install-and-complex-tools \
      --title "Day 05 — Complex tools (init, promote, materialize) + INSTALL.md + Claude Desktop demo" \
      --body-file docs/handoff/day-05-evaluation-report.md
    ```
7. Capture URL. Report completion to Tom with URL, verdict, and a one-line summary that this closes week 1.

NOT-READY: no push, no PR. Return to failing task's loop. Special case: if criterion 6 (demo) is the only failure because Tom hasn't yet filled in the demo evidence, surface that explicitly and pause — don't loop, wait for Tom.

## Out of scope

- **`multi_agent_debate` as a tool** — deliberate non-goal; it's a prompt only. See § "Why `multi_agent_debate` is not a tool" above.
- ChatGPT / Codex MCP config snippets — week 2 work.
- PyPI publish (Test or production) — week 2-3 work.
- DXT bundle, signing, SBOM — v1.1 hardening pass.
- Eval suite (`tests/eval/` workflow-level evals) — week 3.
- Bash 3.2 `declare -A` fix in `scripts/promote-local.sh` — backlog (file separately).
- README headline / value-prop rewrite — week 3 docs work.
- Cleanup of orphan files (`_evaluation-report-template.md` rebase to main) — separate housekeeping.

## Escalation conditions

Escalate for genuine human-judgment calls:

- A target Layer-1 script (e.g., `scripts/materialize-context.sh`) doesn't exist. Surface what you found and ask Tom whether to skip the tool, write a wrapper, or defer.
- FastMCP returns Pydantic validation errors in an unexpected shape (criterion 2/7 can't tell if the consent gate fired). Show what the response looked like and let Tom decide whether the assertion needs adjusting.
- Tom hasn't filled in the Claude Desktop demo by the time you'd otherwise call MERGE-READY. Pause cleanly — don't fabricate evidence and don't ship NOT-READY without flagging Tom directly.
- Total wall-clock time exceeds 1.5 calendar days.

Do NOT escalate for: typos, missed cross-references, `.bak` cleanup, sandbox `.git/*.lock` (surface but don't escalate), routine `pip` warnings.

## After day 5

**Week 1 complete.** Week 2 starts: ChatGPT Desktop Plus + OpenAI Codex CLI MCP config snippets, plus end-to-end testing on each. A separate handoff doc — `day-06-chatgpt-codex-config.md` or equivalent — will be drafted after day-5 lands.

The v1.0 release tag still ships in week 3 day 5 per the plan. Until then, the day-5 PR going green confirms the Claude side of the v1.0 promise (capture → refine → query → archive → promote, plus install demo) is real.

---

## Execution log

_Executor: append entries here as you work. Format:_

_- `[YYYY-MM-DDTHH:MMZ]` — what happened_
