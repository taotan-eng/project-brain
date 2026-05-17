# Day 7 Handoff — Homebrew formula (Scope A) + INSTALL.md rewrite for Claude/Codex/CC

- **Audience**: Claude Code (or any agent operating on the project-brain repo)
- **Date authored**: 2026-05-16
- **Author**: Tom (taotan6@gmail.com) via planning session
- **Estimated effort**: 1-2 person-days
- **Status**: ready
- **Execution mode**: autonomous test-fix-retest loop; escalate only on judgment calls (see § Escalation)
- **Predecessor**: `day-06-chatgpt-codex-config.md` (status: done; PR #6 merged to `main`)
- **Branch**: `day-07/brew-formula` (created at pre-flight)

## TL;DR

Land the **Homebrew formula** (Scope A from the `brew-install-and-daemon` thread). `brew install project-brain-mcp` replaces `uvx project-brain-mcp` as the primary install path for Claude Desktop, Codex CLI, and Claude Code on macOS. The MCP server itself stays stdio — no transport rewrite.

1. **Tap repo**: create `ai-project-brain/homebrew-project-brain` on GitHub (or update if it exists).
2. **Formula**: `Formula/project-brain-mcp.rb` using `virtualenv_install_with_resources` against `python@3.12`.
3. **Release-candidate tag**: cut `v1.0.0-rc.1` in the main repo so the formula has a stable URL.
4. **CI**: GitHub Actions macOS runner builds the bottle and runs the smoke test against the brew-installed binary.
5. **INSTALL.md rewrite**: Claude Desktop / Codex CLI / Claude Code sections lead with `brew install`; `uvx`/`pipx` demoted to a fallback for non-Homebrew users.
6. **compat-matrix**: add a "First-session validated via brew" column or note for the three brew-targeted rows.

**Scope B** (bridge daemon for ChatGPT) is **day-8**. **ChatGPT and Codex E2E demos** shift to days 9-10 so they validate the final brew-based install path, not the now-deprecated `uvx`/`npx` path.

## Context

You are executing **day 7 (week 2 day 2) of the project-brain v1.0 3-week release plan**.

Read these for "why" decisions:

- **Brew-install-and-daemon thread**: `/Users/ttan/workspace/Project-Brain/brew-install-and-daemon.md` — captures the decision space (Scope A vs B, v1.0 stretch vs v1.0.1, macOS-only, separate formulas, Python bridge for Scope B). Tom decided 2026-05-16 to **go with brew for v1.0**; Scope A lands day-7, Scope B day-8.
- **v1.1-install-and-first-run-ux.md § Item 1** — the original "package project-brain-mcp directly" backlog. Day-7 supersedes the `.dxt`-primary recommendation; brew is the chosen path. Cross-reference but don't rewrite the v1.1 doc.
- **Path C decision** (`/Users/ttan/workspace/Project-Brain/path-c-decision.md`): `PROJECT_BRAIN_HOME` is the project root, brain at `<root>/project-brain/`. The brew install must preserve this semantic — config snippets in the new INSTALL.md still set `PROJECT_BRAIN_HOME` to the project root, no `/project-brain` suffix.
- **Day-6 INSTALL.md** — the file that gets rewritten. Specifically: the top-level "Install" section's `uvx project-brain-mcp` command, the `## Claude Desktop config` section's `mcpServers` JSON snippet, the `## OpenAI Codex CLI config` section's TOML snippet, and any references to `uvx` in the Claude Code install path.
- **Convention**: `docs/handoff/README.md` § Workflow + § PR-merge criteria + `_evaluation-report-template.md`.

Day-6 closed week 2 day 1 by shipping the INSTALL.md sections for ChatGPT and Codex with `uvx`/`npx`-based commands and a `pending` row for ChatGPT Plus+ / Codex CLI / Claude Desktop Free demos. Day-7 swaps `uvx` out for brew on the three Apple-host rows; day-8 ships the bridge daemon that lets `brew services start project-brain-bridge` replace the `npx mcp-remote` terminal-loop UX.

## Goal

By the end of this handoff:

1. **Tap repo** `ai-project-brain/homebrew-project-brain` exists on GitHub with `Formula/project-brain-mcp.rb` committed and pushed.
2. **Formula** installs cleanly via `brew install ai-project-brain/project-brain/project-brain-mcp` on macOS 14+ (Sonoma) and macOS 15 (Sequoia). Puts `project-brain-mcp` on PATH. Running the smoke test against the brew-installed binary passes the same assertions as the pipx-editable install.
3. **Release-candidate tag** `v1.0.0-rc.1` exists on `main` in the pack repo. The formula's `url` points at the GitHub-generated tarball for that tag.
4. **CI workflow** at `.github/workflows/brew-formula-build.yml` (in the tap repo) builds the bottle and runs the smoke test on every push to the tap's main branch. Green badge in the tap README.
5. **INSTALL.md rewrite** in the pack repo:
    - Top of file: brew install path leads, `pipx install --editable` is the dev-only fallback, `uvx project-brain-mcp` is the non-Homebrew-user fallback.
    - `## Claude Desktop config`: `mcpServers` JSON snippet uses `"command": "project-brain-mcp", "args": []`. The `uvx` form moves to a "If you prefer not to use Homebrew" subsection.
    - `## OpenAI Codex CLI config`: TOML snippet uses `command = "project-brain-mcp"\nargs = []`. Same uvx-fallback subsection.
    - `## ChatGPT Desktop config`: UNCHANGED for day-7. The `npx -y mcp-remote ...` command stays — day-8 rewrites it to `brew services start project-brain-bridge`.
    - `## Where the brain lives` and `## Multi-brain setup`: unchanged.
6. **compat-matrix.md update**: each of the three brew-targeted host rows (Claude Code, Claude Desktop Pro, Claude Desktop Free) gains a `via brew (macOS)` note in the Notes column. The "First-session validated" column is unchanged for now — the demo runs happen on day-8 (ChatGPT bridge demo gates ChatGPT validation) and day-9-10 (Codex + Claude E2E against brew).
7. **Smoke test** at `scripts/smoke_mcp_roundtrip.py`: no code change required. It already invokes the binary via PATH lookup; whether the binary came from pipx-editable or brew is transparent. Verify by running it after `brew install` succeeds.
8. The **day-7 evaluation report** at `docs/handoff/day-07-evaluation-report.md` documents 8/8 merge criteria pass; the day-7 PR is open against `main` with that report as its body.

## Scope decisions (explicit, to head off creep)

**In scope for day-7:**
- The brew formula for the MCP server (`project-brain-mcp`).
- The release-candidate tag `v1.0.0-rc.1`.
- INSTALL.md rewrite for Claude Desktop, Codex CLI, and Claude Code (the three hosts that get the brew path immediately).
- compat-matrix.md note additions.
- Tap repo CI.

**Out of scope (deliberately deferred to day-8):**
- Bridge daemon for ChatGPT (Scope B).
- INSTALL.md ChatGPT section rewrite.
- launchd plist authoring.
- `brew services` integration.

**Out of scope (deferred to v1.0.1 or v1.1):**
- Linux / linuxbrew validation (formula should be Homebrew-portable; we just don't test it day-7).
- Windows install path (winget / `.msi` / leave for v1.1).
- Submission to `homebrew-core` (the tap is v1.0; core submission is v1.1+).
- PyPI publication of `project-brain-mcp` (the formula sources from GitHub tarball, not PyPI, for now).
- macOS code-signing / notarization of any bundled binaries (formula installs from source via Python virtualenv; no notarization needed).

**Out of scope (don't touch):**
- The MCP server's stdio transport. No HTTP/SSE rewrite.
- Tool schemas, resource URIs, prompt registrations — day-7 is packaging only.
- The workspace-root scratch docs (`brew-install-and-daemon.md`, `v1.1-*.md`, `path-c-decision.md`).
- The meta-brain path references in eval reports (still aspirational; day-7 doesn't fix).

## PR-merge criteria

| # | Criterion | Programmatic check |
|---|---|---|
| 1 | Tap repo exists with formula | `gh repo view ai-project-brain/homebrew-project-brain` returns 200. Repo has `Formula/project-brain-mcp.rb` at HEAD of default branch. |
| 2 | Formula installs cleanly | On a clean macOS environment (CI runner or local fresh user): `brew tap ai-project-brain/project-brain && brew install project-brain-mcp` exits 0; `command -v project-brain-mcp` returns a path under the brew prefix. |
| 3 | Smoke test passes against brew-installed binary | After Criterion 2 succeeds, `python3 scripts/smoke_mcp_roundtrip.py` ends with `MCP SMOKE TEST PASSED`. No edits to the smoke test needed. |
| 4 | Release-candidate tag in main repo | `git tag` lists `v1.0.0-rc.1`; `gh release view v1.0.0-rc.1` shows a published release; the formula's `url` field references the same tag's tarball; the formula's `sha256` matches the actual tarball checksum. |
| 5 | INSTALL.md leads with brew | `head -200 INSTALL.md \| grep -E "^brew install"` finds the brew command. The `## Claude Desktop config` JSON snippet and `## OpenAI Codex CLI config` TOML snippet both use `"command": "project-brain-mcp"` / `command = "project-brain-mcp"` directly (no `uvx`). The `uvx` form appears only in a fallback subsection labeled "If you prefer not to use Homebrew". |
| 6 | ChatGPT section unchanged | `git diff main..HEAD -- INSTALL.md` shows no modifications inside the `## ChatGPT Desktop config` section. Day-7 is additive/rewriting elsewhere; ChatGPT waits for day-8. |
| 7 | compat-matrix notes added | The three brew-targeted rows (Claude Code, Claude Desktop Pro, Claude Desktop Free) each include a `via brew (macOS)` mention in their Notes column. No row's "First-session validated" status changes. |
| 8 | No regression: validator + smoke + no Cowork refs + Conventional Commits | `python3 scripts/verify-tree.py --brain=…` ends `0 errors, 0 warnings`. `python3 scripts/smoke_mcp_roundtrip.py` ends `MCP SMOKE TEST PASSED`. `git grep -E '(AskUserQuestion\|TodoWrite\|mcp__cowork__\|mcp__visualize__)' skills/` returns 0. All day-7 commits use Conventional Commits with scope (`feat(brew):`, `docs(install):`, `chore(release):` etc.). |

Workflow:

- Working branch is `day-07/brew-formula` off `main`.
- Day-7 commits use Conventional Commits with scope (e.g. `feat(brew): author project-brain-mcp formula`, `chore(release): tag v1.0.0-rc.1`, `docs(install): lead with brew`).
- After MERGE-READY, branch is pushed; PR opened against `main` with `docs/handoff/day-07-evaluation-report.md` as body.
- The tap repo is a **separate GitHub repository**. Commits to the tap don't show up in the main repo's PR. The tap's own CI runs independently; criterion 1 + 2 + 3 verify the tap from the main repo's PR review.

## Development loop

Standard. Each task: spec → execute → run validation → consult Common failure modes on fail → ~5 retries max → escalate.

**Sequencing**: Task 1 (tap setup) and Task 3 (rc tag) can run in parallel — they touch different repos. Task 2 (formula authoring) depends on Task 3 (needs the tag URL to point at). Task 4 (CI workflow) depends on Task 2. Tasks 5 + 6 (INSTALL.md + compat-matrix) depend on Task 2 succeeding (so we know the brew command works before documenting it).

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

# 4. Day-6 merged
git fetch origin
git merge-base --is-ancestor origin/day-06/chatgpt-codex-config origin/main \
  || { echo "FAIL: day-6 not merged to main yet"; exit 1; }

# 5. Branch
git checkout -b day-07/brew-formula origin/main

# 6. mcp/ Python package metadata up-to-date
test -f mcp/pyproject.toml \
  || { echo "FAIL: mcp/pyproject.toml missing"; exit 1; }
grep -q '^version' mcp/pyproject.toml \
  || { echo "FAIL: version field missing in pyproject.toml"; exit 1; }
```

If any pre-flight fails, fix it before starting tasks.

## Tasks

### Task 1 — Create / verify the tap repo

The Homebrew tap convention requires a repo named `homebrew-<tap-name>` under a GitHub user or org. The tap here is `ai-project-brain/project-brain`, so the repo name is `ai-project-brain/homebrew-project-brain`.

```bash
# Check if it exists
gh repo view ai-project-brain/homebrew-project-brain >/dev/null 2>&1 \
  && echo "Tap repo exists" \
  || gh repo create ai-project-brain/homebrew-project-brain --public \
       --description "Homebrew tap for project-brain — markdown-in-git decision-tracking MCP server" \
       --license Apache-2.0
```

Clone it locally for working alongside the main repo:

```bash
cd /Users/ttan/workspace/Project-Brain/final
git clone https://github.com/ai-project-brain/homebrew-project-brain.git tap-project-brain
```

The `Formula/` directory is the Homebrew convention. Create it if not present:

```bash
cd /Users/ttan/workspace/Project-Brain/final/tap-project-brain
mkdir -p Formula
```

Commit a scaffold README:

```markdown
# Homebrew Tap — project-brain

`brew install ai-project-brain/project-brain/project-brain-mcp`

Apache 2.0 licensed. See https://github.com/ai-project-brain/project-brain for the underlying package.
```

```bash
git add README.md
git commit -m "chore: scaffold tap README"
git push -u origin main
```

### Task 2 — Tag `v1.0.0-rc.1` in the main repo

The formula needs a stable URL pointing at an immutable tarball. GitHub auto-generates one for every tag. Cut the rc.1 tag now; the formula will reference its tarball.

In the **main repo** (not the tap):

```bash
cd /Users/ttan/workspace/Project-Brain/final/project-brain
git checkout main
git pull origin main
git tag -a v1.0.0-rc.1 -m "v1.0.0-rc.1 — Homebrew formula release candidate

First release candidate for the v1.0 release cycle. Captures day-1
through day-6 work. Used by the day-7 Homebrew formula as the
source-tarball URL. Subsequent rcs (rc.2, etc.) will follow if
week-3 polish touches packaged code."

git push origin v1.0.0-rc.1
```

Create a GitHub Release for the tag (gives the tarball a stable URL + lets users find it in the Releases UI):

```bash
gh release create v1.0.0-rc.1 \
  --title "v1.0.0-rc.1" \
  --notes-file - <<'EOF'
First release candidate of project-brain v1.0. Days 1-6 cumulative work.

Used by the v1.0 Homebrew formula (`ai-project-brain/homebrew-project-brain`) as the source-tarball URL. End users typically install via Homebrew rather than downloading this tarball directly.

See INSTALL.md for install paths.
EOF
```

Verify the tarball URL responds:

```bash
curl -fsI "https://github.com/ai-project-brain/project-brain/archive/refs/tags/v1.0.0-rc.1.tar.gz" \
  | head -1
# Expect: HTTP/2 200 or HTTP/2 302 followed by 200 on the redirect target.
```

Compute the SHA256 the formula will use:

```bash
TARBALL_SHA=$(curl -fsL "https://github.com/ai-project-brain/project-brain/archive/refs/tags/v1.0.0-rc.1.tar.gz" | shasum -a 256 | awk '{print $1}')
echo "TARBALL_SHA=${TARBALL_SHA}"
# Save this — Task 3 inlines it into the formula.
```

### Task 3 — Author `Formula/project-brain-mcp.rb`

In `/Users/ttan/workspace/Project-Brain/final/tap-project-brain/Formula/`, create `project-brain-mcp.rb`:

```ruby
class ProjectBrainMcp < Formula
  include Language::Python::Virtualenv

  desc "Markdown-in-git decision-tracking MCP server"
  homepage "https://github.com/ai-project-brain/project-brain"
  url "https://github.com/ai-project-brain/project-brain/archive/refs/tags/v1.0.0-rc.1.tar.gz"
  sha256 "<TARBALL_SHA from Task 2>"
  license "Apache-2.0"
  head "https://github.com/ai-project-brain/project-brain.git", branch: "main"

  depends_on "python@3.12"

  # Resource blocks for the Python dependencies. Generate via:
  #   brew install homebrew/cask/poet
  #   poet -f project-brain-mcp >> Formula/project-brain-mcp.rb
  # Then move the generated resource blocks above the `def install` method.

  resource "mcp" do
    url "https://files.pythonhosted.org/packages/source/m/mcp/mcp-1.27.1.tar.gz"
    sha256 "<sha from pypi>"
  end

  # ... additional resource blocks for pydantic, anyio, etc. — generate with poet.

  def install
    # The package source lives at mcp/ inside the repo tarball.
    cd "mcp" do
      virtualenv_install_with_resources
    end
  end

  test do
    # Smoke check: binary exists and responds to --help (or equivalent).
    output = shell_output("#{bin}/project-brain-mcp --help 2>&1", 0)
    assert_match(/project-brain/i, output)
  end
end
```

**Generating resource blocks**: the manual list above is illustrative. Use `poet` to generate the full set:

```bash
brew install homebrew/cask/poet  # or: pip install homebrew-pypi-poet
cd /tmp && python3 -m venv pb-poet && source pb-poet/bin/activate
pip install /Users/ttan/workspace/Project-Brain/final/project-brain/mcp
poet -f project-brain-mcp > /tmp/resources.rb
deactivate && rm -rf pb-poet
```

Paste the resource blocks from `/tmp/resources.rb` into the formula. Remove `poet`'s wrapper (`class ProjectBrainMcp < Formula` line); keep only the `resource "<name>" do ... end` blocks.

**Verify the formula style**:

```bash
cd /Users/ttan/workspace/Project-Brain/final/tap-project-brain
brew style --fix Formula/project-brain-mcp.rb
brew audit --strict --new --formula Formula/project-brain-mcp.rb
```

`brew audit --strict --new` checks for first-time-submission issues (homepage reachable, license recognized, no skipped tests, etc.).

**Install and verify**:

```bash
brew install --formula ./Formula/project-brain-mcp.rb
command -v project-brain-mcp
project-brain-mcp --help | head -5
```

If install succeeds, run the smoke test from the main repo against the brew-installed binary:

```bash
cd /Users/ttan/workspace/Project-Brain/final/project-brain
python3 scripts/smoke_mcp_roundtrip.py 2>&1 | tail -5
# Expect: MCP SMOKE TEST PASSED
```

Commit the formula:

```bash
cd /Users/ttan/workspace/Project-Brain/final/tap-project-brain
git add Formula/project-brain-mcp.rb
git commit -m "feat: project-brain-mcp v1.0.0-rc.1 formula"
git push origin main
```

### Task 4 — CI workflow for the tap

In the **tap repo**, create `.github/workflows/brew-formula-build.yml`:

```yaml
name: Build & test formula

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }

      - name: Set up Homebrew
        uses: Homebrew/actions/setup-homebrew@master

      - name: Audit formula
        run: |
          brew style Formula/project-brain-mcp.rb
          brew audit --strict --formula Formula/project-brain-mcp.rb

      - name: Install formula
        run: |
          brew tap-new local/tap
          cp Formula/project-brain-mcp.rb "$(brew --repository)/Library/Taps/local/homebrew-tap/Formula/"
          brew install --formula local/tap/project-brain-mcp

      - name: Verify binary is on PATH
        run: |
          command -v project-brain-mcp
          project-brain-mcp --help | head -5

      - name: Clone main repo and run smoke test
        run: |
          git clone --depth=1 https://github.com/ai-project-brain/project-brain.git /tmp/pb
          cd /tmp/pb
          python3 -m pip install --break-system-packages mcp pydantic anyio
          python3 scripts/smoke_mcp_roundtrip.py
```

Commit and push:

```bash
git add .github/workflows/brew-formula-build.yml
git commit -m "ci: add formula build + smoke test on macOS"
git push origin main
```

Wait for the first CI run; confirm green. If red, the failure is almost always one of:
- Missing `resource` block for a dependency → re-run `poet` and add what's missing.
- Wrong Python version baseline → check `depends_on "python@..."` matches what the package expects.
- Repo-source assumption mismatch → the formula's `cd "mcp" do` assumes the package lives at `mcp/` inside the tarball; verify.

### Task 5 — Rewrite INSTALL.md for Claude Desktop / Codex / Claude Code

Switch to the **main repo** and edit `INSTALL.md`. Three structural changes:

**(a) Top "Install" section** — lead with brew. Replace any current `uvx project-brain-mcp` prominence with:

```markdown
## Install

### macOS — Homebrew (recommended)

```bash
brew tap ai-project-brain/project-brain
brew install project-brain-mcp
```

This installs the `project-brain-mcp` binary on your PATH. No further setup needed for Claude Code; chat-app hosts (Claude Desktop, Codex CLI) need a config edit — see the per-host sections below.

### Other platforms — `pipx` fallback

If you're on Linux / Windows or prefer not to use Homebrew:

```bash
pipx install project-brain-mcp
```

This requires `pipx` (and on Windows / non-stock-Python systems, may require `uv` or `uvx`). Outcomes are identical to the Homebrew install: `project-brain-mcp` ends up on PATH.

### Developer install (editable)

For working on the package itself:

```bash
pipx install --editable /path/to/project-brain/mcp
```

Edits to the source tree take effect on the next stdio session.
```

**(b) `## Claude Desktop config` section** — replace the `mcpServers` JSON snippet's `"command": "uvx", "args": ["project-brain-mcp"]` with the direct binary form:

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

Add a "If you prefer not to use Homebrew" subsection at the end of the Claude Desktop section that retains the old `uvx`-based form for users who installed via `pipx` or `uvx`. Brief and clearly labeled fallback.

**(c) `## OpenAI Codex CLI config` section** — same pattern. The TOML snippet's `command = "uvx"\nargs = ["project-brain-mcp"]` becomes:

```toml
[mcp_servers.project-brain]
command = "project-brain-mcp"
args = []

[mcp_servers.project-brain.env]
PROJECT_BRAIN_HOME = "/absolute/path/to/your/project-root"
```

Same `uvx`-fallback subsection at the section's end.

**(d) Verify additive-only invariant for `## ChatGPT Desktop config`**:

```bash
git diff main..HEAD -- INSTALL.md | grep -A 50 "^@@.*ChatGPT" | head -60
# Expect: zero changes inside the ChatGPT section. Day-7 doesn't touch it.
```

If the diff shows any modification inside the ChatGPT section, revert that hunk — day-8 owns that section.

Commit:

```bash
git add INSTALL.md
git commit -m "docs(install): lead with brew install path; demote uvx to fallback

Claude Desktop, Codex CLI, and Claude Code now install via 'brew install
project-brain-mcp' on macOS. Config snippets use 'command': 'project-brain-mcp'
directly. The pipx/uvx form moves to a fallback subsection for non-Homebrew users.
ChatGPT Desktop section unchanged — day-8 ships the bridge daemon that
swaps 'npx mcp-remote' for 'brew services start project-brain-bridge'."
```

### Task 6 — Update `compat-matrix.md`

Add a `via brew (macOS)` note to the three brew-targeted rows. Don't change the "First-session validated" column for any row — the demos that update that column happen days 9-10.

Find:

```
| Claude Code | Pro+ | stdio | yes (week 1, day-2 smoke test) | Native plugin loader + MCP stdio. Per-project brain via cwd auto-detect; no `PROJECT_BRAIN_HOME` env required. |
```

Replace with:

```
| Claude Code | Pro+ | stdio | yes (week 1, day-2 smoke test) | Native plugin loader + MCP stdio. Per-project brain via cwd auto-detect; no `PROJECT_BRAIN_HOME` env required. Install via `brew install project-brain-mcp` on macOS. |
```

Same pattern for the two `Claude Desktop` rows (Pro and Free). Don't touch the ChatGPT rows (Plus+ and Free) — they're bridge-daemon territory and stay on `npx mcp-remote` until day-8.

Commit:

```bash
git add compat-matrix.md
git commit -m "docs(compat): note brew install path on three macOS-host rows

Claude Code, Claude Desktop Pro, and Claude Desktop Free now reference
'brew install project-brain-mcp'. First-session-validated column unchanged —
demo runs against the brew binary happen days 9-10."
```

### Task 7 — Run smoke test one more time, end-to-end

Final verification that the brew-installed binary works the same as pipx-editable:

```bash
# Uninstall pipx-editable if present to ensure brew is the only source
pipx uninstall project-brain-mcp 2>/dev/null || true

# Verify brew install is on PATH
command -v project-brain-mcp
which project-brain-mcp  # should be under $(brew --prefix)/bin

# Run smoke
cd /Users/ttan/workspace/Project-Brain/final/project-brain
python3 scripts/smoke_mcp_roundtrip.py 2>&1 | tail -5
# Expect: MCP SMOKE TEST PASSED
```

If pass, the brew install path is end-to-end validated. If fail, the failure mode is likely one of:
- `project-brain-mcp` binary missing → reinstall the formula.
- Smoke test imports fail → `pip install --break-system-packages mcp pydantic anyio` in the system Python (smoke test doesn't run in the formula's venv).
- `PROJECT_BRAIN_HOME` resolution chain fails → ensure git walk-up or env var still resolves correctly.

After smoke passes, reinstall pipx-editable for dev workflow (don't leave dev in a brew-only state):

```bash
pipx install --editable /Users/ttan/workspace/Project-Brain/final/project-brain/mcp --force
# 'pipx install --force' overrides the brew-provided binary on PATH. To switch back to brew:
#   pipx uninstall project-brain-mcp
```

### Task 8 — Author the evaluation report

Create `docs/handoff/day-07-evaluation-report.md` following the template at `docs/handoff/_evaluation-report-template.md`.

Frontmatter:

```yaml
- Generated: <ISO 8601 timestamp>
- Plan reference: project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md § 4 (week 2 day 2)
- Handoff: docs/handoff/day-07-brew-formula.md
- Predecessor: day-06 (merged to main via PR #6)
- Week 2 day 2: lands the macOS Homebrew install path (Scope A)
```

Body sections (mirror day-6):
- `## Script adjustments from handoff spec` — any deviations CC made (none expected; if any, document).
- `## Architecture note: separate tap repo`. Brief paragraph explaining the tap is a sibling repo, not a subdir of the main repo.
- `## Merge criteria` — 8-row table mirroring the PR-merge criteria above with ✓ status + evidence.
- `## Files changed (this branch vs main)` — `git diff --stat main...HEAD` output for the main repo. Note the tap repo's changes separately (they're not in this PR's diff).
- `## Commits (this branch)` — `git log --oneline main..HEAD`.
- `## Tap repo state` — short paragraph linking the tap's CI green badge URL and noting the formula version it ships.
- `## Verdict` — MERGE-READY if all 8 criteria pass.

Commit:

```bash
git add docs/handoff/day-07-evaluation-report.md
git commit -m "docs(handoff): day-7 evaluation report — MERGE-READY"
```

### Task 9 — Push and open PR

```bash
git push -u origin day-07/brew-formula

gh pr create \
  --base main \
  --head day-07/brew-formula \
  --title "Day 7: Homebrew formula (Scope A) + INSTALL.md brew rewrite" \
  --body-file docs/handoff/day-07-evaluation-report.md

gh pr checks
```

Confirm CI is green. If anything fails, surface the failure and stop — don't auto-fix.

## Common failure modes

| Failure | Cause | Fix |
|---|---|---|
| `brew install` fails with `Error: undefined method 'virtualenv_install_with_resources'` | Missing `include Language::Python::Virtualenv` at the top of the formula | Add the include line. |
| `brew install` fails with `No matching distribution found for ...` | Missing `resource` block for one of the Python dependencies | Re-run `poet -f project-brain-mcp` and add the missing block(s). |
| `brew install` fails with `Python version mismatch` | `depends_on "python@3.12"` doesn't match what `pyproject.toml` requires | Either bump pyproject's `python_requires` or pin to a different brew python (3.11 vs 3.13). |
| `brew audit --strict` complains about license | Apache-2.0 spelled wrong | Use exactly `Apache-2.0` (case-sensitive). |
| `brew audit --strict` complains about test block | The `test do ... end` block is empty or doesn't assert anything | Add an `assert_match` against `--help` output. |
| Tarball SHA mismatch on `brew install` | Tag was force-pushed or the tarball changed | Recompute SHA via `curl ... \| shasum -a 256`; update formula's `sha256` field. |
| CI fails on macos-latest with "command not found: brew" | The Homebrew setup action failed | Pin to `actions/setup-homebrew@v3` or downgrade to `@master` (most reliable). |
| Smoke test fails after `brew install` with `ModuleNotFoundError: No module named 'mcp'` | The smoke test uses system Python, which doesn't see the formula's venv | Install mcp's deps in system Python: `pip install --break-system-packages mcp pydantic anyio`. The CI job already does this. |
| `gh release create v1.0.0-rc.1` fails with `release already exists` | Someone already cut the tag | Either bump to `rc.2` or `gh release delete v1.0.0-rc.1` and re-create. |
| Day-7 PR diff shows ChatGPT section modified | Accidental edit during INSTALL.md rewrite | Revert the ChatGPT hunk via `git checkout main -- INSTALL.md` then re-apply the Claude/Codex changes carefully. |
| `brew style --fix` modifies the formula in unexpected ways | Style auto-fix changed something subtle (line endings, spacing) | Review the diff; usually safe to keep. |

## Escalation triggers

Stop and surface to Tom if:

- The `ai-project-brain` GitHub org doesn't exist or you don't have write access (tap repo can't be created).
- The formula audit produces warnings about deprecated APIs Homebrew won't accept (rare; means the `virtualenv_install_with_resources` pattern needs a different invocation).
- The smoke test starts failing against the brew-installed binary in a way it doesn't fail against pipx-editable (suggests a real packaging bug).
- `gh release create` requires write access to a repo you don't have (the main repo's release-create permissions).
- The CI run on the tap repo's `macos-latest` runner times out (>15 min); Homebrew installs can be slow but shouldn't exceed that.
- The number of `resource` blocks needed exceeds ~40 (suggests a deep dependency tree that may not be brew-friendly; flag for design review).
- INSTALL.md rewrite collides with day-8's planned ChatGPT bridge work in a way that requires Tom to re-sequence days 7-8.

If you hit one of these, write a short note to `docs/handoff/day-07-escalation.md` explaining what failed and which decision Tom needs to make. Don't push to a PR until escalation is resolved.

## Notes for the next handoff (day-8)

Day-8 ships **Scope B**: the bridge daemon for ChatGPT. Concrete deliverables:

- New formula in the same tap: `project-brain-bridge`. Bundles a small Python `aiohttp`-based stdio→SSE bridge (~200 LOC) plus a launchd plist.
- `brew services start project-brain-bridge` starts the daemon at `127.0.0.1:8787` (with port-fallback logic).
- INSTALL.md `## ChatGPT Desktop config` rewrite — `brew install project-brain-bridge && brew services start project-brain-bridge` replaces the `npx -y mcp-remote ...` terminal command.
- compat-matrix's ChatGPT Plus+ row gets a `via brew bridge (macOS)` note (still pending E2E validation; days 9-10).

Day-9 = ChatGPT E2E demo against the brew bridge.
Day-10 = Codex E2E demo against the brew formula.
Day-11-14 = Week 3 polish + final v1.0.0 release.

Day-8 handoff doc will be authored after day-7 PR merges and the open questions (Python bridge vs npm `mcp-remote` re-use, port-fallback strategy, `brew services` test in CI) get final confirmation from Tom.
