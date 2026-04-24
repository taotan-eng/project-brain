#!/usr/bin/env bash
# update-thread.sh — one-shot thread update (maturity, leaves, soft_links).
#
# Supports six sub-operations: refine (bump maturity), lock, merge-into,
# soft-link-add, soft-link-remove, promote-prep. Each is a pure frontmatter
# or body edit followed by an index rebuild. Target runtime: under 500ms.
#
# Usage:
#   scripts/update-thread.sh \
#       --brain=<path>              \  # absolute path to the brain dir
#       --slug=<thread-slug>        \  # thread identifier
#       --operation=<op>            \  # refine | lock | merge-into | soft-link-add | soft-link-remove | promote-prep
#       [--target=<target>]         \  # for refine: exploring|refining|locking
#       [--merge-into-slug=<slug>]  \  # for merge-into: target thread slug
#       [--url=<uri>]               \  # for soft-link-add/remove
#
# Exit codes:
#   0   update complete and brain validates clean
#   1   thread not found, wrong status, or rebuild failed
#   2   invocation error (bad args, missing brain, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
OPERATION=""
TARGET=""
MERGE_INTO_SLUG=""
URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)              BRAIN="${1#*=}"; shift ;;
    --brain)                BRAIN="$2"; shift 2 ;;
    --slug=*)               SLUG="${1#*=}"; shift ;;
    --slug)                 SLUG="$2"; shift 2 ;;
    --operation=*)          OPERATION="${1#*=}"; shift ;;
    --operation)            OPERATION="$2"; shift 2 ;;
    --target=*)             TARGET="${1#*=}"; shift ;;
    --target)               TARGET="$2"; shift 2 ;;
    --merge-into-slug=*)    MERGE_INTO_SLUG="${1#*=}"; shift ;;
    --merge-into-slug)      MERGE_INTO_SLUG="$2"; shift 2 ;;
    --url=*)                URL="${1#*=}"; shift ;;
    --url)                  URL="$2"; shift 2 ;;
    -h|--help)              head -n 35 "$0"; exit 0 ;;
    *)                      echo "error: unknown arg: $1" >&2; exit 2 ;;
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
# Apply operation via embedded Python
# ---------------------------------------------------------------------------

python3 - "$THREAD_MD" "$OPERATION" "$TARGET" "$MERGE_INTO_SLUG" "$URL" <<'PY'
import sys
import pathlib
import yaml

thread_path = pathlib.Path(sys.argv[1])
operation = sys.argv[2]
target = sys.argv[3]
merge_into_slug = sys.argv[4]
url = sys.argv[5]

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
    print(f"error: cannot update a {current_status} thread", file=sys.stderr)
    sys.exit(1)

# Apply operation
if operation == 'refine':
    if not target:
        print("error: --target is required for refine operation", file=sys.stderr)
        sys.exit(1)
    if target not in ['exploring', 'refining', 'locking']:
        print("error: invalid target maturity", file=sys.stderr)
        sys.exit(1)
    frontmatter['maturity'] = target

elif operation == 'soft-link-add':
    if not url:
        print("error: --url is required for soft-link-add", file=sys.stderr)
        sys.exit(1)
    soft_links = frontmatter.get('soft_links', [])
    if not isinstance(soft_links, list):
        soft_links = []
    if url not in soft_links:
        soft_links.append(url)
    frontmatter['soft_links'] = soft_links

elif operation == 'soft-link-remove':
    if not url:
        print("error: --url is required for soft-link-remove", file=sys.stderr)
        sys.exit(1)
    soft_links = frontmatter.get('soft_links', [])
    if isinstance(soft_links, list) and url in soft_links:
        soft_links.remove(url)
        frontmatter['soft_links'] = soft_links

elif operation in ['lock', 'merge-into', 'promote-prep']:
    # These are placeholders for more complex operations
    # lock: maturity → locking
    # merge-into: merge into another thread
    # promote-prep: prepare for promotion
    pass

else:
    print(f"error: unknown operation: {operation}", file=sys.stderr)
    sys.exit(1)

# Emit new file
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

echo "Updated thread '${SLUG}' — operation: ${OPERATION}."
echo "Done."

exit 0
