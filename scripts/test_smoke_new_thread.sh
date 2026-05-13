#!/usr/bin/env bash
# Smoke test — new-thread.sh executes end-to-end with no Cowork env vars.
#
# Pass condition:
#   - scratch brain is scaffolded
#   - new-thread.sh creates the thread + template files + indexes
#   - verify-tree.py reports 0 errors against the scratch brain
#
# Pins the host-neutral cross-harness contract: a fresh terminal with bash,
# python3, and the pack on disk should be able to run the scripts without
# any Cowork-/Claude-Code-specific env var.

set -euo pipefail

# Strip every host-specific env var so we know we're testing the
# host-neutral path.
unset CLAUDE_PLUGIN_ROOT
unset PROJECT_BRAIN_PACK_ROOT
unset PROJECT_BRAIN_HOME
unset COWORK_WORKSPACE_FOLDER
unset CODEX_PROJECT_ROOT
unset CLAUDE_PROJECT_ROOT

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "${HERE}/.." && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

BRAIN="$TMP/brain"
mkdir -p "$BRAIN/threads" "$BRAIN/tree" "$BRAIN/archive"

cat > "$BRAIN/config.yaml" <<YAML
brain_version: "1.0.0-rc4"
primary_project: smoketest
projects:
  smoketest:
    title: "Smoke Test"
    brain: $BRAIN
domains: [example]
YAML

# Minimal CONVENTIONS.md — frontmatter is required by verify-tree.
cat > "$BRAIN/CONVENTIONS.md" <<'MD'
---
id: smoke-conventions
title: Smoke conventions
version: 1.0.0-smoke
status: draft
---

# Smoke conventions

Scaffolding file for the smoke test. Content is intentionally minimal.
MD

cat > "$BRAIN/thread-index.md" <<'MD'
# Thread index

## Active

| Slug | Title | Owner | Maturity | Updated |
|------|-------|-------|----------|---------|

## Parked

## Archived
MD

cat > "$BRAIN/current-state.md" <<'MD'
# Current state
MD

# Tree NODE.md — required schema fields per V-06/V-10.
mkdir -p "$BRAIN/tree"
cat > "$BRAIN/tree/NODE.md" <<'MD'
---
id: tree-root
title: Tree root
created_at: 2026-05-13T00:00:00Z
owner: smoke@example.com
primary_project: smoketest
related_projects: []
soft_links: []
status: decided
node_type: node
domain: /
children: []
---

# Tree root
MD

# ---------------------------------------------------------------------------
# Invoke new-thread.sh
# ---------------------------------------------------------------------------

"${HERE}/new-thread.sh" \
  --brain="$BRAIN" \
  --slug=smoke-test-thread \
  --title="Smoke test thread" \
  --purpose="end-to-end check that new-thread runs host-agnostically" \
  --primary-project=smoketest \
  --owner=smoke@example.com

# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

THREAD_DIR="$BRAIN/threads/smoke-test-thread"

[ -d "$THREAD_DIR" ] \
  || { echo "FAIL: thread dir $THREAD_DIR not created"; exit 1; }

for f in thread.md decisions-candidates.md open-questions.md; do
  [ -f "$THREAD_DIR/$f" ] \
    || { echo "FAIL: $THREAD_DIR/$f not created"; exit 1; }
done

command grep -q '^id: smoke-test-thread$' "$THREAD_DIR/thread.md" \
  || { echo "FAIL: id frontmatter missing in thread.md"; head -20 "$THREAD_DIR/thread.md"; exit 1; }

command grep -q 'smoke-test-thread' "$BRAIN/thread-index.md" \
  || { echo "FAIL: thread-index.md not updated"; cat "$BRAIN/thread-index.md"; exit 1; }

# Validator clean against the scratch brain
if ! python3 "${HERE}/verify-tree.py" --brain="$BRAIN" 2>&1 | tail -1 | command grep -q "0 errors"; then
  echo "FAIL: validator dirty after new-thread"
  python3 "${HERE}/verify-tree.py" --brain="$BRAIN"
  exit 1
fi

# Confirm helper works when sourced
. "${HERE}/_plugin_root.sh"
RESOLVED="$(_plugin_root)" \
  || { echo "FAIL: _plugin_root failed to resolve with no env vars set"; exit 1; }
[ "$RESOLVED" = "$PACK_ROOT" ] \
  || { echo "FAIL: _plugin_root auto-detect resolved to '$RESOLVED', expected '$PACK_ROOT'"; exit 1; }

echo "SMOKE TEST PASSED"
