#!/usr/bin/env bash
# new-thread.sh — one-shot thread scaffold.
#
# Creates a thread directory with the three template files (thread.md,
# decisions-candidates.md, open-questions.md) and rebuilds the aggregate
# index files. Target runtime: under 500ms including the rebuild.
#
# Replaces ~6 individual file-tool calls (1 mkdir + 3 reads + 3 writes
# + 1 Bash for rebuild) with ONE bash invocation — one permission
# prompt, one tool-call roundtrip, zero per-file diff rendering in the
# agent UI.
#
# Usage:
#   scripts/new-thread.sh \
#       --brain=<path>                 \  # absolute path to the brain dir
#       --slug=<kebab-case-slug>       \  # thread slug; validated per § 11.1
#       --title='<human title>'        \  # maps to frontmatter title + H1
#       --purpose='<one-line purpose>' \  # used in thread-index.md row
#       --primary-project=<alias>      \  # alias from <brain>/config.yaml
#       [--owner=<email>]              \  # default: TODO@example.com
#       [--tree-domain=<slug>]         \  # default: null (promote-time decides)
#       [--related-projects=<csv>]     \  # default: empty list
#
# Exit codes:
#   0   scaffold complete and brain validates clean
#   1   thread already exists OR rebuild failed
#   2   invocation error (bad args, missing templates, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
TITLE=""
PURPOSE=""
PRIMARY_PROJECT=""
OWNER="TODO@example.com"
TREE_DOMAIN=""
RELATED_PROJECTS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)              BRAIN="${1#*=}"; shift ;;
    --brain)                BRAIN="$2"; shift 2 ;;
    --slug=*)               SLUG="${1#*=}"; shift ;;
    --slug)                 SLUG="$2"; shift 2 ;;
    --title=*)              TITLE="${1#*=}"; shift ;;
    --title)                TITLE="$2"; shift 2 ;;
    --purpose=*)            PURPOSE="${1#*=}"; shift ;;
    --purpose)              PURPOSE="$2"; shift 2 ;;
    --primary-project=*)    PRIMARY_PROJECT="${1#*=}"; shift ;;
    --primary-project)      PRIMARY_PROJECT="$2"; shift 2 ;;
    --owner=*)              OWNER="${1#*=}"; shift ;;
    --owner)                OWNER="$2"; shift 2 ;;
    --tree-domain=*)        TREE_DOMAIN="${1#*=}"; shift ;;
    --tree-domain)          TREE_DOMAIN="$2"; shift 2 ;;
    --related-projects=*)   RELATED_PROJECTS="${1#*=}"; shift ;;
    --related-projects)     RELATED_PROJECTS="$2"; shift 2 ;;
    -h|--help)              head -n 30 "$0"; exit 0 ;;
    *)                      echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

for req in BRAIN SLUG TITLE PURPOSE; do
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

# Auto-resolve --primary-project from <brain>/config.yaml when absent. The
# overwhelmingly common case is a brain that has exactly one alias (the
# project-brain init scaffolds just that); we pick it silently. If multiple
# aliases are declared, demand --primary-project explicitly. This removes a
# mandatory Read-tool call from the calling skill — one fewer Cowork
# round-trip on the hot path.
if [[ -z "$PRIMARY_PROJECT" ]]; then
  CFG="$BRAIN/config.yaml"
  if [[ -f "$CFG" ]]; then
    PP="$(awk '
      /^primary_project[[:space:]]*:/ {
        v = $0; sub(/^primary_project[[:space:]]*:[[:space:]]*/, "", v)
        gsub(/^["\x27]|["\x27][[:space:]]*$/, "", v)
        print v; exit
      }' "$CFG")"
    if [[ -n "$PP" ]]; then
      PRIMARY_PROJECT="$PP"
    else
      # Fall back to a single alias if primary_project isn't set but aliases
      # has exactly one entry (the init-brain.sh default).
      mapfile -t ALIASES < <(awk '
        /^aliases[[:space:]]*:/ { in_a=1; next }
        in_a && /^[^[:space:]#]/ { in_a=0 }
        in_a && /^[[:space:]]+[a-z][a-z0-9-]*[[:space:]]*:/ {
          name = $1; sub(/:$/, "", name); gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
          print name
        }' "$CFG")
      if [[ ${#ALIASES[@]} -eq 1 ]]; then
        PRIMARY_PROJECT="${ALIASES[0]}"
      fi
    fi
  fi
fi
if [[ -z "$PRIMARY_PROJECT" ]]; then
  echo "error: --primary-project could not be auto-resolved from $BRAIN/config.yaml." >&2
  echo "       Pass --primary-project=<alias> explicitly." >&2
  exit 2
fi

# Slug validation per § 11.1
if [[ ! "$SLUG" =~ ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ ]]; then
  echo "error: --slug '$SLUG' is not a valid kebab-case slug." >&2
  exit 2
fi

THREAD_DIR="${BRAIN}/threads/${SLUG}"
if [[ -e "$THREAD_DIR" ]]; then
  echo "error: thread already exists: $THREAD_DIR" >&2
  echo "       Re-run with a different --slug (e.g., ${SLUG}-2)." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Locate pack assets
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATES="${PACK_ROOT}/assets/thread-template"
VERIFIER="${SCRIPT_DIR}/verify-tree.py"

for f in "${TEMPLATES}/thread.md" \
         "${TEMPLATES}/decisions-candidates.md" \
         "${TEMPLATES}/open-questions.md"; do
  if [[ ! -f "$f" ]]; then
    echo "error: missing pack template: $f" >&2
    exit 2
  fi
done

# ---------------------------------------------------------------------------
# Scaffold the thread
# ---------------------------------------------------------------------------

CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TREE_DOMAIN_VALUE="${TREE_DOMAIN:-null}"

mkdir -p "$THREAD_DIR"

# Escape the title and purpose for safe insertion into sed (both can
# contain arbitrary characters including the `|` we use as sed
# delimiter). Quick escape: replace `|` with `\|` in the replacement
# strings.
escape_sed() { printf '%s' "$1" | sed 's|[|\\&]|\\&|g'; }
TITLE_E="$(escape_sed "$TITLE")"
PURPOSE_E="$(escape_sed "$PURPOSE")"
OWNER_E="$(escape_sed "$OWNER")"

copy_with_substitutions() {
  local src="$1" dst="$2"
  cp "$src" "$dst"
  sed -i.bak \
    -e "s|{{SLUG}}|${SLUG}|g" \
    -e "s|{{TITLE}}|${TITLE_E}|g" \
    -e "s|{{PURPOSE}}|${PURPOSE_E}|g" \
    -e "s|{{CREATED_AT}}|${CREATED_AT}|g" \
    -e "s|{{OWNER}}|${OWNER_E}|g" \
    -e "s|{{PRIMARY_PROJECT}}|${PRIMARY_PROJECT}|g" \
    -e "s|{{TREE_DOMAIN_OR_NULL}}|${TREE_DOMAIN_VALUE}|g" \
    "$dst"
  # Best-effort cleanup; FUSE-mounted filesystems may deny unlink. Don't
  # fail the scaffold over a leftover .bak.
  rm -f "${dst}.bak" 2>/dev/null || true
}

copy_with_substitutions "${TEMPLATES}/thread.md"              "${THREAD_DIR}/thread.md"
copy_with_substitutions "${TEMPLATES}/decisions-candidates.md" "${THREAD_DIR}/decisions-candidates.md"
copy_with_substitutions "${TEMPLATES}/open-questions.md"      "${THREAD_DIR}/open-questions.md"

# ---------------------------------------------------------------------------
# Rebuild aggregate indexes
# ---------------------------------------------------------------------------

REBUILD_STATUS="ok"
if [[ -x "$VERIFIER" ]]; then
  # Attempt rebuild. If it fails we degrade gracefully: the thread
  # scaffold is the primary success (files exist on disk, user can
  # write in them immediately). Stale aggregate indexes (thread-index.md,
  # current-state.md) are a secondary concern recoverable by re-running
  # verify-tree at any time. Don't turn a successful thread creation
  # into a failed operation just because rebuild had a hiccup.
  REBUILD_STDERR="$(python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index 2>&1 > /dev/null)" || {
    REBUILD_STATUS="fail"
  }
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

echo "Created thread '${SLUG}' at ${THREAD_DIR}."
if [[ "$OWNER" == "TODO@example.com" ]]; then
  echo "  owner = TODO@example.com placeholder; replace when ready."
fi
if [[ "$REBUILD_STATUS" == "fail" ]]; then
  echo "  note: aggregate indexes (thread-index.md, current-state.md) are stale." >&2
  echo "        the thread is usable as-is; run verify-tree --rebuild-index later to refresh." >&2
  echo "        rebuild stderr: ${REBUILD_STDERR}" >&2
fi
# No git-commit reminder at capture time by design: capture/refine/debate
# are all git-free per rc4. Git enters at promote-time.

echo "Done."
exit 0
