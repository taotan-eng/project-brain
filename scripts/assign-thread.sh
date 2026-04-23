#!/usr/bin/env bash
# assign-thread.sh — one-shot thread assignment mutation.
#
# Supports four operations: --add, --remove, --set, --clear.
# Mutates assigned_to frontmatter field and appends audit line to body.
# Target runtime: under 500ms.
#
# Usage:
#   scripts/assign-thread.sh \
#       --brain=<path>           \  # absolute path to the brain dir
#       --slug=<thread-slug>     \  # thread identifier
#       --add=<handles>          \  # comma-separated handles to add
#       [--add, --remove, --set, --clear] # exactly one operation
#       [--actor=<email>]        \  # who performed this; default: TODO@example.com
#       [--note='<note>']        \  # optional explanation
#
# Exit codes:
#   0   assignment complete and brain validates clean
#   1   thread not found, wrong status, or rebuild failed
#   2   invocation error (bad args, missing brain, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
OPERATION=""  # add, remove, set, clear
HANDLES=""
ACTOR="TODO@example.com"
NOTE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)      BRAIN="${1#*=}"; shift ;;
    --brain)        BRAIN="$2"; shift 2 ;;
    --slug=*)       SLUG="${1#*=}"; shift ;;
    --slug)         SLUG="$2"; shift 2 ;;
    --add=*)        OPERATION="add"; HANDLES="${1#*=}"; shift ;;
    --add)          OPERATION="add"; HANDLES="$2"; shift 2 ;;
    --remove=*)     OPERATION="remove"; HANDLES="${1#*=}"; shift ;;
    --remove)       OPERATION="remove"; HANDLES="$2"; shift 2 ;;
    --set=*)        OPERATION="set"; HANDLES="${1#*=}"; shift ;;
    --set)          OPERATION="set"; HANDLES="$2"; shift 2 ;;
    --clear)        OPERATION="clear"; shift ;;
    --actor=*)      ACTOR="${1#*=}"; shift ;;
    --actor)        ACTOR="$2"; shift 2 ;;
    --note=*)       NOTE="${1#*=}"; shift ;;
    --note)         NOTE="$2"; shift 2 ;;
    -h|--help)      head -n 30 "$0"; exit 0 ;;
    *)              echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate args
# ---------------------------------------------------------------------------

for req in BRAIN SLUG OPERATION; do
  if [[ -z "${!req}" ]]; then
    echo "error: --${req,,} is required." >&2
    exit 2
  fi
done

if [[ "$OPERATION" == "clear" && -n "$HANDLES" ]]; then
  echo "error: --clear does not take handles." >&2
  exit 2
fi

if [[ "$OPERATION" != "clear" && -z "$HANDLES" ]]; then
  echo "error: --${OPERATION} requires handles." >&2
  exit 2
fi

if [[ ! -d "$BRAIN" ]]; then
  echo "error: brain directory not found: $BRAIN" >&2
  exit 2
fi
BRAIN="$(cd "$BRAIN" && pwd)"

if [[ ! -f "$BRAIN/CONVENTIONS.md" ]]; then
  echo "error: $BRAIN does not look like a project-brain." >&2
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
# Apply assignment via embedded Python
# ---------------------------------------------------------------------------

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - "$THREAD_MD" "$OPERATION" "$HANDLES" "$ACTOR" "$NOTE" "$NOW" <<'PY'
import sys
import pathlib
import yaml
import re

thread_path = pathlib.Path(sys.argv[1])
operation = sys.argv[2]
handles_str = sys.argv[3]
actor = sys.argv[4]
note = sys.argv[5]
now_ts = sys.argv[6]

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

current_status = frontmatter.get('status')
if current_status == 'archived':
    print("error: cannot assign to archived thread", file=sys.stderr)
    sys.exit(1)

# Get current assigned_to list
current_assigned = frontmatter.get('assigned_to', [])
if not isinstance(current_assigned, list):
    current_assigned = []

# Parse handles
new_handles = [h.strip() for h in handles_str.split(',') if h.strip()] if handles_str else []

# Apply operation
if operation == 'add':
    new_assigned = list(set(current_assigned) | set(new_handles))
elif operation == 'remove':
    new_assigned = [h for h in current_assigned if h not in new_handles]
elif operation == 'set':
    new_assigned = new_handles
elif operation == 'clear':
    new_assigned = []
    frontmatter.pop('assigned_to', None)
else:
    print(f"error: unknown operation: {operation}", file=sys.stderr)
    sys.exit(1)

if operation != 'clear':
    frontmatter['assigned_to'] = new_assigned

# Append audit line to body
audit_handles = ','.join(new_handles) if new_handles else '(field removed)'
audit_line = f"- {now_ts} — {actor} — assign-thread: {operation} {audit_handles}"
if note:
    audit_line += f" — {note}"

# Find or create Assignment history section
body_lines = body_text.split('\n')
found_section = False
for i, line in enumerate(body_lines):
    if line.startswith('## Assignment history'):
        found_section = True
        body_lines.insert(i + 1, audit_line)
        break

if not found_section:
    body_lines.append('')
    body_lines.append('## Assignment history')
    body_lines.append(audit_line)

new_body_text = '\n'.join(body_lines)

# Emit new file
fm_output = yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
new_text = f"---\n{fm_output}---\n{new_body_text}"
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

echo "Updated assignments on thread '${SLUG}' — operation: ${OPERATION}."

exit 0
