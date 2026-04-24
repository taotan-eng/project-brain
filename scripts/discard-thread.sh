#!/usr/bin/env bash
# discard-thread.sh — one-shot thread discard (move to archive).
#
# Moves thread from threads/ to archive/, flips status to archived,
# removes maturity, adds archive metadata, and rebuilds indexes.
# Target runtime: under 500ms.
#
# Usage:
#   scripts/discard-thread.sh \
#       --brain=<path>           \  # absolute path to the brain dir
#       --slug=<thread-slug>     \  # thread identifier
#       --reason='<reason>'      \  # "why discarded"
#       [--by=<email>]           \  # actor email; default: TODO@example.com
#
# Exit codes:
#   0   discard complete and brain validates clean
#   1   thread not found, wrong status, or rebuild failed
#   2   invocation error (bad args, missing brain, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
REASON=""
BY="TODO@example.com"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)      BRAIN="${1#*=}"; shift ;;
    --brain)        BRAIN="$2"; shift 2 ;;
    --slug=*)       SLUG="${1#*=}"; shift ;;
    --slug)         SLUG="$2"; shift 2 ;;
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

for req in BRAIN SLUG REASON; do
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

THREAD_DIR="${BRAIN}/threads/${SLUG}"
THREAD_MD="${THREAD_DIR}/thread.md"

if [[ ! -f "$THREAD_MD" ]]; then
  echo "error: thread not found: $THREAD_MD" >&2
  exit 1
fi

ARCHIVE_DIR="${BRAIN}/archive/${SLUG}"
if [[ -d "$ARCHIVE_DIR" ]]; then
  echo "error: archive path already exists: $ARCHIVE_DIR" >&2
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

python3 - "$THREAD_MD" "$NOW" "$BY" "$REASON" <<'PY'
import sys
import pathlib
import yaml

thread_path = pathlib.Path(sys.argv[1])
now_ts = sys.argv[2]
by_email = sys.argv[3]
reason = sys.argv[4]

text = thread_path.read_text()

# Split frontmatter and body
lines = text.split('\n')
if not lines[0].startswith('---'):
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
    frontmatter = yaml.safe_load(fm_text) or {}
except Exception as e:
    print(f"error: failed to parse frontmatter: {e}", file=sys.stderr)
    sys.exit(1)

if not isinstance(frontmatter, dict):
    print("error: frontmatter is not a dict", file=sys.stderr)
    sys.exit(1)

current_status = frontmatter.get('status', 'unknown')

if current_status not in ['active', 'parked']:
    print(f"error: cannot discard a {current_status} thread", file=sys.stderr)
    sys.exit(1)

# Flip status to archived, remove maturity
frontmatter['status'] = 'archived'
frontmatter.pop('maturity', None)

# Add archive metadata
frontmatter['archived_at'] = now_ts
frontmatter['archived_by'] = by_email
frontmatter['discard_reason'] = reason

# Remove park metadata if present
frontmatter.pop('parked_at', None)
frontmatter.pop('parked_by', None)
frontmatter.pop('parked_reason', None)
frontmatter.pop('unpark_trigger', None)

# Emit new file
fm_output = yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
new_text = f"---\n{fm_output}---\n{body_text}"
thread_path.write_text(new_text)

sys.exit(0)
PY

# ---------------------------------------------------------------------------
# Move directory from threads/ to archive/
# ---------------------------------------------------------------------------

mkdir -p "${BRAIN}/archive"
mv "$THREAD_DIR" "$ARCHIVE_DIR"

# ---------------------------------------------------------------------------
# Rebuild aggregate indexes
# ---------------------------------------------------------------------------

if [[ -x "$VERIFIER" ]]; then
  if ! python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index 2>/dev/null; then
    echo "error: verify-tree --rebuild-index failed." >&2
    echo "       Thread moved to archive but indexes stale. Run verify-tree --rebuild-index to repair." >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

echo "Discarded thread '${SLUG}' to archive (reason: ${REASON})."
echo "Done."

exit 0
