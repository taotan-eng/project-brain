#!/usr/bin/env bash
# park-thread.sh — one-shot thread park/unpark operation.
#
# Flips thread status between active and parked, manages park metadata
# (parked_at, parked_by, parked_reason, unpark_trigger), and rebuilds
# the aggregate index files. Target runtime: under 500ms.
#
# Usage:
#   scripts/park-thread.sh \
#       --brain=<path>        \  # absolute path to the brain dir
#       --slug=<thread-slug>  \  # thread identifier
#       --reason='<reason>'   \  # for park mode; "why paused"
#       [--unpark]            \  # unpark mode (default: park)
#       [--by=<email>]        \  # actor email; default: TODO@example.com
#       [--trigger='<trigger>'] # optional unpark trigger for park mode
#
# Exit codes:
#   0   park/unpark complete and brain validates clean
#   1   thread not found, wrong status, or rebuild failed
#   2   invocation error (bad args, missing brain, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
REASON=""
UNPARK=0
BY="TODO@example.com"
TRIGGER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)      BRAIN="${1#*=}"; shift ;;
    --brain)        BRAIN="$2"; shift 2 ;;
    --slug=*)       SLUG="${1#*=}"; shift ;;
    --slug)         SLUG="$2"; shift 2 ;;
    --reason=*)     REASON="${1#*=}"; shift ;;
    --reason)       REASON="$2"; shift 2 ;;
    --unpark)       UNPARK=1; shift ;;
    --by=*)         BY="${1#*=}"; shift ;;
    --by)           BY="$2"; shift 2 ;;
    --trigger=*)    TRIGGER="${1#*=}"; shift ;;
    --trigger)      TRIGGER="$2"; shift 2 ;;
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

if [[ ! -d "$BRAIN" ]]; then
  echo "error: brain directory not found: $BRAIN" >&2
  exit 2
fi
BRAIN="$(cd "$BRAIN" && pwd)"

if [[ ! -f "$BRAIN/CONVENTIONS.md" ]]; then
  echo "error: $BRAIN does not look like a project-brain (missing CONVENTIONS.md)." >&2
  exit 2
fi

THREAD_MD="${BRAIN}/threads/${SLUG}/thread.md"
if [[ ! -f "$THREAD_MD" ]]; then
  echo "error: thread not found: $THREAD_MD" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Locate pack assets
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERIFIER="${SCRIPT_DIR}/verify-tree.py"

# ---------------------------------------------------------------------------
# Apply park/unpark mutation via embedded Python
# ---------------------------------------------------------------------------

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - "$THREAD_MD" "$UNPARK" "$NOW" "$BY" "$REASON" "$TRIGGER" <<'PY'
import sys
import pathlib
import yaml
import re

thread_path = pathlib.Path(sys.argv[1])
unpark_mode = int(sys.argv[2]) == 1
now_ts = sys.argv[3]
by_email = sys.argv[4]
reason = sys.argv[5]
trigger = sys.argv[6]

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

if unpark_mode:
    # unpark: parked → active, remove park metadata
    if current_status != 'parked':
        print(f"error: cannot unpark a {current_status} thread", file=sys.stderr)
        sys.exit(1)

    frontmatter['status'] = 'active'
    frontmatter.pop('parked_at', None)
    frontmatter.pop('parked_by', None)
    frontmatter.pop('parked_reason', None)
    frontmatter.pop('unpark_trigger', None)
else:
    # park: active → parked, add park metadata
    if current_status != 'active':
        print(f"error: cannot park a {current_status} thread", file=sys.stderr)
        sys.exit(1)

    if not reason:
        print("error: reason is required for park mode", file=sys.stderr)
        sys.exit(1)

    frontmatter['status'] = 'parked'
    frontmatter['parked_at'] = now_ts
    frontmatter['parked_by'] = by_email
    frontmatter['parked_reason'] = reason
    if trigger:
        frontmatter['unpark_trigger'] = trigger

# Emit new frontmatter with yaml.safe_dump
fm_output = yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
new_text = f"---\n{fm_output}---\n{body_text}"
thread_path.write_text(new_text)

sys.exit(0)
PY

# ---------------------------------------------------------------------------
# Rebuild aggregate indexes
# ---------------------------------------------------------------------------

if [[ -x "$VERIFIER" ]]; then
  if ! python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index 2>/dev/null; then
    echo "error: verify-tree --rebuild-index failed." >&2
    echo "       Thread updated but indexes stale. Run verify-tree --rebuild-index to repair." >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

if [[ "$UNPARK" -eq 1 ]]; then
  echo "Unparked thread '${SLUG}' — status: active."
else
  echo "Parked thread '${SLUG}' (reason: ${REASON}) — status: parked."
fi
echo "Done."

exit 0
