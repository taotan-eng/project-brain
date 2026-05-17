# Day-7 Escalation — Pack-root resolution fails under brew/pip install

- Raised: 2026-05-17T02:00:00Z
- Reporter: Claude Code (claude-opus-4-7), executing `day-07-brew-formula.md`
- Triggering criterion: § Escalation triggers — "The smoke test starts failing against the brew-installed binary in a way it doesn't fail against pipx-editable (suggests a real packaging bug)."

## Tap CI run that failed

- Latest run: https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25978377701
- Failure step: `Clone main repo + run smoke test`
- Symptom: `AssertionError: expected >=14 prompts, got 0: []`
- Earlier steps (style, audit, install, binary on PATH): all green.
- Build artifact: `🍺 /opt/homebrew/Cellar/project-brain-mcp/1.0.0-rc.4: 988 files, 19.9MB, built in 9 minutes 11 seconds`. The brew install itself worked; the formula is structurally sound.

## What's actually broken

`mcp/src/project_brain_mcp/_subprocess.py::find_pack_root()` walks up from `Path(__file__).resolve().parent` looking for the canonical pack triplet (`CONVENTIONS.md` + `skills/` + `scripts/`).

For `pipx install --editable /path/to/mcp`, `__file__` resolves to `/path/to/mcp/src/project_brain_mcp/_subprocess.py`, and the walk-up succeeds at `/path/to/` (the repo root) which has the triplet.

For `brew install project-brain-mcp` (and equivalently for any non-editable `pip install`), `__file__` resolves to `/opt/homebrew/Cellar/project-brain-mcp/1.0.0-rc.4/libexec/lib/python3.12/site-packages/project_brain_mcp/_subprocess.py`. Walking up never reaches the pack triplet — only `mcp/src/project_brain_mcp/*.py` gets packaged into the wheel; the surrounding pack files (`skills/`, `scripts/`, `CONVENTIONS.md`, `assets/`) don't ship with the install.

Downstream effects:

- **Prompts**: `prompts.PROMPT_SKILLS = _discover_skills()` returns `()` because `find_pack_root()` raises and the caller swallows the error. `prompts/list` returns 0 items. Smoke test asserts ≥14 and crashes.
- **Tools that shell to Layer-1 scripts**: `_subprocess.run_script(name, argv)` calls `find_pack_root()` first to locate `scripts/<name>.sh`. Raises immediately. Every everyday tool (`new_thread`, `list_threads`, `verify_tree`, etc.) is non-functional.
- **Resources**: read from `$PROJECT_BRAIN_HOME` (the user's brain dir, not the pack). These still work.

End-user impact: a brew-installed `project-brain-mcp` exposes 4 tools (`new_thread`, `list_threads`, `verify_tree`, `run_skill`) plus another 13 day-4/day-5 tools, but every one of them crashes when invoked because the underlying scripts can't be found. The MCP handshake succeeds and `tools/list` returns the schema, so it looks like it's working until the agent actually calls a tool.

## Why pipx-editable hides this

`pipx install --editable` symlinks the package into site-packages instead of copying it. `Path(__file__)` then points at the original source tree, which IS embedded in the pack repo. The walk-up succeeds by coincidence of the editable layout. Every non-editable install hits the bug.

This means the day-3..day-6 smoke-test suite never caught it — my local environment used `pipx install --editable` throughout. The bug is real but has been latent since day-3 when the MCP package was first scaffolded.

## Decision Tom needs to make

Pick one of four paths. Each has a different scope and a different impact on the v1.0 timeline.

### Option A — Bundle the pack files into the Python wheel

Update `mcp/pyproject.toml` to include `skills/`, `scripts/`, `CONVENTIONS.md`, `assets/` as package data. Hatch's `[tool.hatch.build.targets.wheel]` doesn't natively support paths outside the project root (`mcp/`), so this needs either:
- Move `mcp/pyproject.toml` to the repo root and restructure as a single Python package containing everything (large refactor).
- Add a hatch build hook that copies the pack files into `mcp/` before the wheel is built (medium refactor).
- Switch `mcp/` to a setuptools-with-MANIFEST.in setup that pulls files from `../`.

Effort: 0.5–1 day. Adds ~5–10 MB to wheel size (skills + scripts + assets). Doesn't change runtime behavior — `find_pack_root()` walks up from the installed `project_brain_mcp/` package dir and finds the bundled triplet in the same directory.

### Option B — Have the formula install pack files alongside the binary

In `def install`, after the venv install, copy `skills/`, `scripts/`, `CONVENTIONS.md`, `assets/` into `prefix/share/project-brain-mcp/`. Update `find_pack_root()` to check that brew-aware path as a high-priority source before the walk-up. Optionally provide a wrapper at `bin/project-brain-mcp` that sets `PROJECT_BRAIN_PACK_ROOT` to `share/project-brain-mcp/`.

Effort: 0.5 day. Formula change is straightforward. `find_pack_root()` gains a brew-aware probe (or env-var-default approach). Works for brew but NOT for pipx/pip — those users would still need to set `PROJECT_BRAIN_PACK_ROOT` manually OR clone the repo, contradicting the day-7 goal that pipx be a fallback.

### Option C — Make `find_pack_root()` more aggressive

Add new search sources to `find_pack_root()`:
- Cwd walk-up (the smoke test runs from `/tmp/pb` which IS a pack — would resolve there).
- Known install locations (`brew --prefix` + `share/project-brain-mcp/`, `/usr/local/share/project-brain-mcp/`, etc.).

Effort: 0.25 day. Mostly code change in `_subprocess.py`. Smoke test would pass without other changes because its cwd is the cloned pack. End users would still need to chdir to a pack-clone before invoking the MCP server — which contradicts the "drop-in install" promise.

### Option D — Defer brew to v1.0.1, ship pipx-editable as v1.0's only path

Revert the day-7 INSTALL.md rewrite. Keep `uvx`/`pipx` as the documented install paths for v1.0. Move the brew formula work to v1.0.1, properly bundled (Option A) once the packaging refactor is done. compat-matrix.md keeps the day-7 "brew install" notes as "planned for v1.0.1" instead of "use this now."

Effort: 0 day (revert in progress). v1.0 ships without brew but with a working install path. v1.0.1 ships brew. Doesn't gate v1.0 on a packaging refactor.

### Recommendation

**Option D for v1.0** + **Option A for v1.0.1**. Reasoning:

1. The day-7 spec budgeted 1–2 person-days for "package as brew formula." None of those days budgeted for the packaging refactor Option A needs. Bundling pack files into the wheel changes the project's build shape and benefits from review beyond day-7's scope.
2. Option B and C are partial fixes — they make brew work but leave pipx broken (or weirdly cwd-dependent). End-user docs would need to caveat each install path differently, which is exactly the kind of friction v1.0 is trying to avoid.
3. Day-7 unblocked the formula side (the build works! 30 resources resolve, the binary lands). That work isn't wasted — it lives on `homebrew-project-brain` and the rc.4 tag. v1.0.1 picks up from there with a fixed wheel.
4. v1.0 still has a clean install story via pipx (day-3..day-5 path). The day-5 demo went green on pipx-editable. The audience that wanted brew won't get it until v1.0.1, but they'll get a working pipx install today.

## What's on disk right now

- `day-07/brew-formula` branch (local + pushed) has commits:
  - `1ec0351 docs(compat): note brew install path on three macOS-host rows`
  - `24adb74 docs(install): lead with brew install path; demote uvx to fallback`
  - Plus the day-7 handoff doc + eval-report draft (staged but not committed).
- Tap repo `ai-project-brain/homebrew-project-brain` exists with a working formula (build green, smoke fails). Tap CI run: https://github.com/ai-project-brain/homebrew-project-brain/actions/runs/25978377701
- Main repo tag `v1.0.0-rc.4` published with release: https://github.com/ai-project-brain/project-brain/releases/tag/v1.0.0-rc.4

Per § Escalation triggers' instruction ("Don't push to a PR until escalation is resolved"), **the day-7 PR has NOT been opened**. The branch is local-only until you decide which option to take.

## Side notes (not blocking the decision)

- Tag bumped from `v1.0.0-rc.1` to `v1.0.0-rc.4` because rc.1/rc.2/rc.3/rc4 were all already published from the April alpha era. Documented in the eval-report draft.
- The tap repo's CI workflow has had two iterations (path-based audit → name-based; dual-tap conflict → canonical-tap-only). Both fixes were small CI-config changes, not packaging issues. Worth keeping.
- `homebrew-pypi-poet` is broken on modern Python (`pkg_resources` removal). Wrote a custom 50-line Python generator that uses curl + jq + PyPI's JSON API; ~3-second runtime. Captured at `/tmp/gen_resources.py` and used to generate the 30 resource blocks in the formula. Worth keeping for v1.0.1.
