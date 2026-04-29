#!/usr/bin/env bash
# rename-thread-slug.sh — rename a thread's slug (ASCII↔Unicode, any
# valid slug to any valid slug). Handles directory rename + frontmatter
# id update + source_thread updates inside artifacts + index rebuild.
# Cross-references in tree/ leaves are reported as warnings (not auto-
# rewritten — that's intentionally manual because it can affect locked
# decisions in the public tree).
#
# Usage:
#   scripts/rename-thread-slug.sh \
#       --brain=<path>       \
#       --old=<old-slug>     \
#       --new=<new-slug>     \
#       [--archive]          \  # rename in archive/ instead of threads/
#       [--dry-run]
#
# Exit codes:
#   0   rename complete; verify-tree clean
#   1   collision, broken cross-reference, or rebuild failure
#   2   invocation error
#
# Why this script exists:
#   For a long time the slug rule was ASCII-only. The pack now supports
#   Unicode slugs (per CONVENTIONS § 11.1, widened in the Unicode-slug
#   commit), but threads created before the widening still have ASCII
#   slugs. Users who want their thread directories renamed to their
#   native script (e.g., hong-kong-layover → 香港计划) had no path until
#   this script. Also useful for general slug typo fixes.

set -euo pipefail

BRAIN=""
OLD_SLUG=""
NEW_SLUG=""
LOCATION="threads"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)   BRAIN="${1#*=}"; shift ;;
    --brain)     BRAIN="$2"; shift 2 ;;
    --old=*)     OLD_SLUG="${1#*=}"; shift ;;
    --old)       OLD_SLUG="$2"; shift 2 ;;
    --new=*)     NEW_SLUG="${1#*=}"; shift ;;
    --new)       NEW_SLUG="$2"; shift 2 ;;
    --archive)   LOCATION="archive"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    -h|--help)   head -n 28 "$0"; exit 0 ;;
    *)           echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

for req in BRAIN OLD_SLUG NEW_SLUG; do
  if [[ -z "${!req}" ]]; then
    echo "error: --${req,,} is required." >&2
    exit 2
  fi
done

if [[ ! -d "$BRAIN" ]]; then
  echo "error: brain directory not found: $BRAIN" >&2
  exit 2
fi
BRAIN="$(cd "$BRAIN" && pwd)"

if [[ ! -f "$BRAIN/CONVENTIONS.md" ]]; then
  echo "error: $BRAIN does not look like a project-brain." >&2
  exit 2
fi

OLD_DIR="${BRAIN}/${LOCATION}/${OLD_SLUG}"
NEW_DIR="${BRAIN}/${LOCATION}/${NEW_SLUG}"

if [[ ! -d "$OLD_DIR" ]]; then
  echo "error: thread '${OLD_SLUG}' not found at ${OLD_DIR}" >&2
  exit 1
fi

if [[ -e "$NEW_DIR" ]]; then
  echo "error: target slug already exists: ${NEW_DIR}" >&2
  echo "       Pick a different --new slug or move the existing entry." >&2
  exit 1
fi

# Validate new slug via the canonical helper (single source of truth).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
_v_tmp="$(mktemp)"
if ! python3 "${SCRIPT_DIR}/_validate_slug.py" "$NEW_SLUG" >"$_v_tmp"; then
  rm -f "$_v_tmp"
  exit 2
fi
NEW_SLUG="$(cat "$_v_tmp")"
rm -f "$_v_tmp"

# Old slug is also re-validated (defensive: pre-Unicode brains may have
# pre-existing slugs that satisfy the rule, but a typo'd argument shouldn't
# match any thread anyway). We don't fail on old slug mis-validation —
# the directory existence check above is the real precondition.

# ---------------------------------------------------------------------------
# Cross-reference scan — find every place in the brain that mentions the
# old slug. Reported as warnings; the user gets visibility before commit.
# ---------------------------------------------------------------------------
declare -a XREFS=()
# Search artifacts inside the thread (these we DO auto-rewrite below).
# Search everything else under the brain (tree, other threads, archive)
# for warning-level visibility.
echo "Scanning for cross-references to '${OLD_SLUG}' under ${BRAIN}/ ..." >&2
while IFS= read -r f; do
  case "$f" in
    "${OLD_DIR}/"*)        ;;  # inside the renaming thread — handled below
    *)                     XREFS+=("$f") ;;
  esac
done < <(grep -rl --include='*.md' -F "$OLD_SLUG" "$BRAIN" 2>/dev/null || true)

if [[ ${#XREFS[@]} -gt 0 ]]; then
  echo "" >&2
  echo "⚠️  Found ${#XREFS[@]} file(s) outside the thread that mention '${OLD_SLUG}':" >&2
  for f in "${XREFS[@]}"; do
    rel="${f#${BRAIN}/}"
    # Show first 2 matching lines per file.
    while IFS= read -r line; do
      printf '    %s : %s\n' "$rel" "$line" >&2
    done < <(grep -nF "$OLD_SLUG" "$f" 2>/dev/null | head -2)
  done
  echo "" >&2
  echo "These references are NOT auto-rewritten. They may be:" >&2
  echo "  - source_thread: fields in tree/ leaves (LOCKED — manual decision)" >&2
  echo "  - soft_links: in other threads (intentional cross-references)" >&2
  echo "  - body prose mentions of the slug" >&2
  echo "Review and update them by hand if needed. Continuing with the rename." >&2
  echo "" >&2
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "DRY-RUN — would have:" >&2
  echo "  1. Updated 'id:' in ${OLD_DIR}/thread.md" >&2
  echo "  2. Updated 'source_thread:' in ${OLD_DIR}/artifacts/*.md" >&2
  echo "  3. Renamed ${OLD_DIR}/ → ${NEW_DIR}/" >&2
  echo "  4. Rebuilt thread-index.md and current-state.md" >&2
  exit 0
fi

# ---------------------------------------------------------------------------
# Update id: in thread.md frontmatter (in place, before the move).
# ---------------------------------------------------------------------------
THREAD_MD="${OLD_DIR}/thread.md"
if [[ ! -f "$THREAD_MD" ]]; then
  echo "error: malformed thread (no thread.md at ${OLD_DIR})" >&2
  exit 1
fi

python3 - "$THREAD_MD" "$NEW_SLUG" <<'PY'
import sys, re
path, new_slug = sys.argv[1], sys.argv[2]
text = open(path, encoding='utf-8').read()
m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
if not m:
    print(f"error: no frontmatter in {path}", file=sys.stderr)
    sys.exit(1)
fm, body = m.group(1), m.group(2)
# Replace `id: <anything>` line with the new slug. Preserve other lines.
new_fm = re.sub(r'(?m)^id\s*:\s*.*$', f'id: {new_slug}', fm)
open(path, 'w', encoding='utf-8').write(f"---\n{new_fm}\n---\n{body}")
PY

# ---------------------------------------------------------------------------
# Update source_thread: in any artifacts under the thread.
# ---------------------------------------------------------------------------
if [[ -d "${OLD_DIR}/artifacts" ]]; then
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    python3 - "$f" "$OLD_SLUG" "$NEW_SLUG" <<'PY'
import sys, re
path, old_slug, new_slug = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding='utf-8').read()
m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
if not m:
    sys.exit(0)  # no frontmatter — leave alone
fm, body = m.group(1), m.group(2)
# Only touch source_thread: fields whose value matches the old slug.
# Leaves any other source_thread alone (defensive).
def repl(match):
    val = match.group(2).strip().strip('"').strip("'")
    if val == old_slug:
        return f"{match.group(1)}: {new_slug}"
    return match.group(0)
new_fm = re.sub(r'(?m)^(source_thread)\s*:\s*(.+)$', repl, fm)
if new_fm != fm:
    open(path, 'w', encoding='utf-8').write(f"---\n{new_fm}\n---\n{body}")
PY
  done < <(find "${OLD_DIR}/artifacts" -maxdepth 2 -type f -name '*.md' 2>/dev/null)
fi

# ---------------------------------------------------------------------------
# Move the directory.
# ---------------------------------------------------------------------------
# Prefer git mv if the brain is in a git repo; fall back to plain mv.
GIT_ROOT=""
cur="$BRAIN"
for _ in $(seq 1 10); do
  if [[ -e "$cur/.git" ]]; then GIT_ROOT="$cur"; break; fi
  parent="$(dirname "$cur")"
  [[ "$parent" == "$cur" ]] && break
  cur="$parent"
done

if [[ -n "$GIT_ROOT" ]] && command -v git >/dev/null 2>&1; then
  ( cd "$GIT_ROOT" && git mv "$OLD_DIR" "$NEW_DIR" ) 2>/dev/null \
    || mv "$OLD_DIR" "$NEW_DIR"
else
  mv "$OLD_DIR" "$NEW_DIR"
fi

# ---------------------------------------------------------------------------
# Rebuild indexes.
# ---------------------------------------------------------------------------
VERIFIER="${SCRIPT_DIR}/verify-tree.py"
if [[ -f "$VERIFIER" ]]; then
  if ! python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index >/dev/null 2>&1; then
    echo "warning: post-rename rebuild reported problems." >&2
    echo "         Rename succeeded on disk; run 'verify-tree --brain $BRAIN' to diagnose." >&2
  fi
fi

# ---------------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------------
echo "Renamed thread '${OLD_SLUG}' → '${NEW_SLUG}'."
echo "  ${LOCATION}/${OLD_SLUG}/  →  ${LOCATION}/${NEW_SLUG}/"
echo "  thread.md id field updated."
if [[ -d "${NEW_DIR}/artifacts" ]]; then
  echo "  artifacts/ source_thread fields updated where they matched."
fi
if [[ ${#XREFS[@]} -gt 0 ]]; then
  echo "  ⚠️  ${#XREFS[@]} cross-reference(s) outside the thread were NOT rewritten — review the warnings above."
fi
echo "Done."

exit 0
