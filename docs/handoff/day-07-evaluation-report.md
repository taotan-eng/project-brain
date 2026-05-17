# Day-7 Evaluation Report

- Generated: 2026-05-17T01:15:00Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 2 day 2)
- Handoff: `docs/handoff/day-07-brew-formula.md`
- Predecessor: day-06 (merged to main via PR #6, commit `b78258c`)
- Week 2 day 2: lands the macOS Homebrew install path (Scope A)

## Architecture note: separate tap repo

The Homebrew tap lives in a **separate GitHub repository**, `ai-project-brain/homebrew-project-brain`, not as a subdirectory of the main pack repo. This follows Homebrew's `homebrew-<tap-name>` naming convention so that `brew tap ai-project-brain/project-brain` resolves correctly. Commits to the tap repo (formula + CI workflow) don't appear in this PR's diff — they were pushed directly to the tap's `main` branch as a sibling artifact. Tap CI runs independently on every push to the tap's main; criterion 2 + 3 + tap-CI-green together attest to the formula's correctness.

The tap repo's `Formula/project-brain-mcp.rb` ships `project-brain-mcp v1.0.0-rc.4`, sourcing from the GitHub-generated tarball of the matching tag in the main repo.

## Script adjustments from handoff spec

Three deviations from the handoff, all transparently documented in their criterion's evidence cell or below:

1. **Tag bumped from `v1.0.0-rc.1` to `v1.0.0-rc.4`.** The April-era release cycle had already published rc.1 / rc.2 / rc.3 / rc4 tags pointing at alpha-stage commits unrelated to the v1.0 release arc. Per § Common failure modes ("Either bump to `rc.2` or `gh release delete` and re-create"), bumped to the next free dot-versioned tag (`v1.0.0-rc.4`) rather than rewriting/deleting an existing public tag. All references in the formula, INSTALL.md, and eval criterion 4 use `v1.0.0-rc.4`.
2. **CI workflow audits by formula name, not by path.** The handoff's spec workflow used `brew audit --strict --formula Formula/project-brain-mcp.rb`. Modern brew (5.1.11) disables path-based audit; only `brew audit <tap>/<formula>` is supported. The CI workflow uses `brew tap-new local/test --no-git`, copies the formula in, then audits via `brew audit --strict --formula local/test/project-brain-mcp`. Same coverage; correct invocation. First CI run on the original spec failed at this exact step; second run uses the corrected workflow.
3. **Local `brew install` was blocked by sandbox file permissions** for `/opt/homebrew/Library/Taps/homebrew/homebrew-core` (homebrew-core not cloned on this machine; sandbox forbids writing there). CI on `macos-latest` is the canonical validator — those runners come with homebrew-core pre-tapped. Criterion 2's "Formula installs cleanly" is validated via the tap CI run; local install was unable to reach the actual `virtualenv_install_with_resources` step here.

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Tap repo exists with formula | ✓ | `gh repo view ai-project-brain/homebrew-project-brain` returns 200. `Formula/project-brain-mcp.rb` is at HEAD of default branch `main`. Tap repo URL: https://github.com/ai-project-brain/homebrew-project-brain |
| 2 | Formula installs cleanly on macOS | <CI_RESULT> | Validated by tap CI run on `macos-latest`. Local `brew install` was blocked by sandbox file-permission limitations on `/opt/homebrew/Library/Taps/homebrew/` (homebrew-core not present on this sandbox; can't be cloned). |
| 3 | Smoke test passes against brew-installed binary | <CI_RESULT> | Tap CI clones the main repo at v1.0.0-rc.4, runs `python3 scripts/smoke_mcp_roundtrip.py` after the brew install. The smoke test invokes the binary via PATH lookup — transparent whether it came from brew or pipx-editable. Locally re-verified the smoke test still passes end-to-end (with pipx-editable binary): `MCP SMOKE TEST PASSED`. |
| 4 | Release-candidate tag in main repo | ✓ | `git tag` lists `v1.0.0-rc.4` (bumped from rc.1 to skirt the pre-existing April-era tag — see § Script adjustments #1). `gh release view v1.0.0-rc.4` shows published release. Formula's `url` field references the matching GitHub tarball; `sha256` is `403065b70e7a586be15e0ac0c1ef71700233024c4d7ccaa980c8480a275db00b`, computed via `curl ... \| shasum -a 256`. |
| 5 | INSTALL.md leads with brew | ✓ | Top of file (`## Install`): first subsection `### macOS — Homebrew (recommended)` has `brew install project-brain-mcp`. `## Claude Desktop config` JSON snippet uses `"command": "project-brain-mcp", "args": []`. `## OpenAI Codex CLI config` TOML snippet uses `command = "project-brain-mcp"\nargs = []`. The `uvx` form moved to "If you prefer not to use Homebrew" subsections in each. `pipx install` is documented as the cross-platform fallback. |
| 6 | ChatGPT section unchanged | ✓ | `diff <(git show main:INSTALL.md \| awk ChatGPT section) <(awk ChatGPT section INSTALL.md)` returns exit 0 (sections IDENTICAL). Day-8 owns the ChatGPT bridge-daemon rewrite. |
| 7 | compat-matrix notes added | ✓ | All three brew-targeted rows (Claude Code Pro+, Claude Desktop Pro, Claude Desktop Free) include `Install via brew install project-brain-mcp on macOS.` in their Notes column. `command grep -c` for that exact phrase returns 3. No "First-session validated" status changes. |
| 8 | No regression | ✓ | Validator: `0 errors, 0 warnings (44 artifacts walked)`. Smoke test (against pipx-editable binary): `MCP SMOKE TEST PASSED`. Cowork refs in `skills/`: 0. Day-7 commits use Conventional Commits with scope (`docs(install):`, `docs(compat):`, `feat(brew):` etc.). |

## Files changed (this branch vs main)

```
 INSTALL.md       | 84 ++++++++++++++++++++++++++++++++++++++++++++++----------
 compat-matrix.md |  6 ++--
 2 files changed, 72 insertions(+), 18 deletions(-)
```

Plus the `docs/handoff/day-07-brew-formula.md` handoff doc + the `docs/handoff/day-07-evaluation-report.md` you're reading now.

Tap repo changes (NOT in this PR — sibling repo):

```
 Formula/project-brain-mcp.rb           | 178 +++++++++++ (new)
 README.md                              |  18 +++ (new)
 .github/workflows/brew-formula-build.yml |  57 ++ (new)
```

## Commits (this branch)

```
  <updated by script before push>
```

## Tap repo state

- URL: https://github.com/ai-project-brain/homebrew-project-brain
- Default branch: `main`
- Formula: `Formula/project-brain-mcp.rb` ships `project-brain-mcp v1.0.0-rc.4`
- CI workflow: `.github/workflows/brew-formula-build.yml` builds + smoke-tests on `macos-latest` for every push.
- CI run for the final commit: <RUN_URL>

## Verdict

<VERDICT>
