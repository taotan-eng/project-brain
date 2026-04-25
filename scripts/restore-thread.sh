#!/usr/bin/env bash
# restore-thread.sh — bring an archived thread back to active.
#
# The inverse of discard-thread. Moves archive/<slug>/ back to threads/<slug>/,
# flips frontmatter status archived→active, restores maturity (defaults to
# refining unless --maturity=<value> is passed), strips the archive metadata
# (archived_at, archived_by, discard_reason), rebuilds aggregate indexes.
#
# Usage:
#   scripts/restore-thread.sh \
#       --brain=<path>            \
#       --slug=<slug>             \
#       [--maturity=<exploring|refining|locking>]  \
#       [--reason='<why restoring>']  \  # optional; appended to thread body audit
#       [--by=<email>]
#
# Exit codes:
#   0   restored cleanly
#   1   operational failure (thread not in archive, target already exists, etc.)
#   2   invocation error

set -euo pipefail

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
MATURITY="refining"
REASON=""
BY="TODO@example.com"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)      BRAIN="${1#*=}"; shift ;;
    --brain)        BRAIN="$2"; shift 2 ;;
    --slug=*)       SLUG="${1#*=}"; shift ;;
    --slug)         SLUG="$2"; shift 2 ;;
    --maturity=*)   MATURITY="${1#*=}"; shift ;;
    --maturity)     MATURITY="$2"; shift 2 ;;
    --reason=*)     REASON="${1#*=}"; shift ;;
    --reason)       REASON="$2"; shift 2 ;;
    --by=*)         BY="${1#*=}"; shift ;;
    --by)           BY="$2"; shift 2 ;;
    -h|--help)      head -n 25 "$0"; exit 0 ;;
    *)              echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate args
# ---------------------------------------------------------------------------

for req in BRAIN SLUG; do
  if [[ -z "${!req}" ]]; then
    echo "error: --${req,,} is required." >&2
    exit 2
  fi
done

case "$MATURITY" in
  exploring|refining|locking) ;;
  *) echo "error: --maturity must be exploring|refining|locking (got '$MATURITY')." >&2; exit 2 ;;
esac

if [[ ! -d "$BRAIN" ]]; then
  echo "error: brain directory not found: $BRAIN" >&2
  exit 2
fi
BRAIN="$(cd "$BRAIN" && pwd)"

if [[ ! -f "$BRAIN/CONVENTIONS.md" ]]; then
  echo "error: $BRAIN does not look like a project-brain." >&2
  exit 2
fi

ARCHIVE_DIR="${BRAIN}/archive/${SLUG}"
ARCHIVE_MD="${ARCHIVE_DIR}/thread.md"
TARGET_DIR="${BRAIN}/threads/${SLUG}"

if [[ ! -f "$ARCHIVE_MD" ]]; then
  echo "error: archived thread not found: $ARCHIVE_MD" >&2
  exit 1
fi

if [[ -d "$TARGET_DIR" ]]; then
  echo "error: target already exists: $TARGET_DIR" >&2
  echo "       (an active thread with the same slug — pick a different slug or" >&2
  echo "        rename the existing one first)" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Locate pack assets
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERIFIER="${SCRIPT_DIR}/verify-tree.py"

# ---------------------------------------------------------------------------
# Flip frontmatter via embedded Python
# ---------------------------------------------------------------------------

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - "$ARCHIVE_MD" "$NOW" "$BY" "$MATURITY" "$REASON" <<'PY'
import sys, pathlib
try:
    import yaml
except ImportError:
    print("error: PyYAML required for frontmatter update.", file=sys.stderr)
    sys.exit(1)

thread_path = pathlib.Path(sys.argv[1])
now_ts, by_email, maturity, reason = sys.argv[2:6]

text = thread_path.read_text()
lines = text.split('\n')
if not lines or not lines[0].startswith('---'):
    print("error: frontmatter not found", file=sys.stderr)
    sys.exit(1)

end_idx = None
for i in range(1, len(lines)):
    if lines[i].startswith('---'):
        end_idx = i
        break
if end_idx is None:
    print("error: malformed frontmatter", file=sys.stderr)
    sys.exit(1)

fm_text = '\n'.join(lines[1:end_idx])
body_text = '\n'.join(lines[end_idx + 1:])

try:
    fm = yaml.safe_load(fm_text) or {}
except Exception as e:
    print(f"error: failed to parse frontmatter: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(fm, dict):
    print("error: frontmatter is not a dict", file=sys.stderr)
    sys.exit(1)

current_status = fm.get('status', 'unknown')
if current_status != 'archived':
    print(f"error: cannot restore a {current_status} thread (expected: archived)", file=sys.stderr)
    sys.exit(1)

# Flip back to active + restore maturity. Strip all archive metadata.
fm['status'] = 'active'
fm['maturity'] = maturity
for k in ('archived_at', 'archived_by', 'discard_reason'):
    fm.pop(k, None)
fm['last_modified_at'] = now_ts
fm['last_modified_by'] = by_email

# Append a one-line audit trail to the body so the restoration is visible
# even after the metadata is gone.
audit_line = f"\n<!-- {now_ts} — restored from archive by {by_email}"
if reason:
    audit_line += f" — {reason}"
audit_line += " -->\n"
new_body = body_text.rstrip() + "\n" + audit_line

fm_output = yaml.safe_dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
thread_path.write_text(f"---\n{fm_output}---\n{new_body}")
PY

# ---------------------------------------------------------------------------
# Move directory from archive/ back to threads/
# ---------------------------------------------------------------------------

mkdir -p "${BRAIN}/threads"
mv "$ARCHIVE_DIR" "$TARGET_DIR"

# ---------------------------------------------------------------------------
# Rebuild aggregate indexes
# ---------------------------------------------------------------------------

if [[ -f "$VERIFIER" ]]; then
  if ! python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index > /dev/null 2>&1; then
    echo "warning: post-restore rebuild reported problems." >&2
    echo "         Thread is restored on disk; run 'verify-tree --brain $BRAIN' to diagnose." >&2
  fi
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

echo "Restored thread '${SLUG}' from archive (status=active, maturity=${MATURITY})."
if [[ -n "$REASON" ]]; then
  echo "  reason: ${REASON}"
fi
echo "Done."

exit 0
