#!/usr/bin/env bash
# record-artifact.sh — one-shot artifact capture.
#
# Captures intermediate outputs (debate results, benchmarks, analyses,
# sketches, raw CSV/images) into a thread. Default mode: each input becomes
# a separate file under threads/<slug>/artifacts/ (markdown, with enforced
# frontmatter) or threads/<slug>/attachments/ (non-markdown/binary, V-06
# exempt). transcript.md always gets a breadcrumb line pointing at the
# created file. Append mode: content goes directly into transcript.md under
# a timestamped H2 — no separate file.
#
# Usage:
#   scripts/record-artifact.sh \
#       --brain=<path>                   \  # absolute path to the brain dir
#       --slug=<thread-slug>             \  # target thread
#       --title='<human title>'          \  # H1 + transcript breadcrumb label
#       (--file=<path> [--file=<path>]*  \  # one or more existing files to ingest
#         | --content='<markdown>'       \  # or inline markdown content
#         | --stdin)                     \  # or read body from stdin
#       [--artifact-kind=<label>]        \  # debate|analysis|benchmark|sketch|reference|other (default: artifact)
#       [--append]                       \  # write into transcript.md instead of a separate file
#       [--by=<email>]                   \  # actor email; default TODO@example.com
#       [--no-rebuild]                   \  # skip verify-tree --rebuild-index (tests only)
#
# Exit codes:
#   0   artifact(s) written and brain validates clean
#   1   validation failed after write (the artifact is still on disk — run
#       verify-tree to see specifics and fix)
#   2   invocation error (bad args, thread not found, inputs missing, etc.)

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
TITLE=""
FILES=()
CONTENT=""
USE_STDIN=0
ARTIFACT_KIND="artifact"
APPEND=0
BY="TODO@example.com"
NO_REBUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)              BRAIN="${1#*=}"; shift ;;
    --brain)                BRAIN="$2"; shift 2 ;;
    --slug=*)               SLUG="${1#*=}"; shift ;;
    --slug)                 SLUG="$2"; shift 2 ;;
    --title=*)              TITLE="${1#*=}"; shift ;;
    --title)                TITLE="$2"; shift 2 ;;
    --file=*)               FILES+=("${1#*=}"); shift ;;
    --file)                 FILES+=("$2"); shift 2 ;;
    --content=*)            CONTENT="${1#*=}"; shift ;;
    --content)              CONTENT="$2"; shift 2 ;;
    --stdin)                USE_STDIN=1; shift ;;
    --artifact-kind=*)      ARTIFACT_KIND="${1#*=}"; shift ;;
    --artifact-kind)        ARTIFACT_KIND="$2"; shift 2 ;;
    --append)               APPEND=1; shift ;;
    --by=*)                 BY="${1#*=}"; shift ;;
    --by)                   BY="$2"; shift 2 ;;
    --no-rebuild)           NO_REBUILD=1; shift ;;
    -h|--help)              head -n 35 "$0"; exit 0 ;;
    *)                      echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# 2. Validate args
# ---------------------------------------------------------------------------

for req in BRAIN SLUG TITLE; do
  if [[ -z "${!req}" ]]; then
    echo "error: --${req,,} is required." >&2
    exit 2
  fi
done

# Exactly one content source
src_count=0
[[ ${#FILES[@]} -gt 0 ]] && src_count=$((src_count+1))
[[ -n "$CONTENT" ]]      && src_count=$((src_count+1))
[[ $USE_STDIN -eq 1 ]]   && src_count=$((src_count+1))
if [[ $src_count -eq 0 ]]; then
  echo "error: one of --file=, --content=, or --stdin is required." >&2
  exit 2
fi
if [[ $src_count -gt 1 ]]; then
  echo "error: --file, --content, --stdin are mutually exclusive." >&2
  exit 2
fi

if [[ ! -d "$BRAIN" ]]; then
  echo "error: brain directory not found: $BRAIN" >&2
  exit 2
fi
BRAIN="$(cd "$BRAIN" && pwd)"
if [[ ! -f "$BRAIN/CONVENTIONS.md" ]]; then
  echo "error: $BRAIN does not look like a project-brain (missing CONVENTIONS.md)." >&2
  exit 2
fi

THREAD_DIR=""
for loc in threads archive; do
  if [[ -d "$BRAIN/$loc/$SLUG" ]]; then
    THREAD_DIR="$BRAIN/$loc/$SLUG"
    break
  fi
done
if [[ -z "$THREAD_DIR" ]]; then
  echo "error: thread '$SLUG' not found in $BRAIN/threads/ or $BRAIN/archive/." >&2
  exit 2
fi

# Slug sanity — the frontmatter + path-match check (V-22) lives in the
# validator; this is just a cheap pre-check so we don't write nonsense.
if [[ ! "$SLUG" =~ ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ ]]; then
  echo "error: --slug '$SLUG' is not a valid kebab-case slug." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 3. Resolve body source → a single temp file holding what we'll write.
# ---------------------------------------------------------------------------

TMPBODY="$(mktemp)"
trap 'rm -f "$TMPBODY"' EXIT

if [[ $USE_STDIN -eq 1 ]]; then
  cat > "$TMPBODY"
elif [[ -n "$CONTENT" ]]; then
  printf '%s' "$CONTENT" > "$TMPBODY"
fi
# (for --file mode, bodies are copied per-file in the loop below)

CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATE_FOR_ID="$(date -u +%Y-%m-%d)"

# Derive a slug fragment for filenames from the title (lowercase, non-alnum → '-').
title_slug() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -e 's/[^a-z0-9]/-/g' -e 's/--*/-/g' -e 's/^-//' -e 's/-$//'
}
TITLE_SLUG="$(title_slug "$TITLE")"
[[ -z "$TITLE_SLUG" ]] && TITLE_SLUG="untitled"

# ---------------------------------------------------------------------------
# 4. APPEND MODE — straight into transcript.md, no separate file.
# ---------------------------------------------------------------------------

if [[ $APPEND -eq 1 ]]; then
  TRANSCRIPT="$THREAD_DIR/transcript.md"
  # Create transcript.md if it doesn't exist yet; it has no frontmatter
  # contract (kind=transcript is in KINDS_WITHOUT_FRONTMATTER).
  touch "$TRANSCRIPT"
  {
    printf '\n## %s — %s\n\n' "$CREATED_AT" "$TITLE"
    printf '_by %s · appended via record-artifact._\n\n' "$BY"
    if [[ ${#FILES[@]} -gt 0 ]]; then
      for src in "${FILES[@]}"; do
        if [[ ! -f "$src" ]]; then
          echo "error: --file path not found: $src" >&2
          exit 2
        fi
        printf '<!-- source: %s -->\n' "$src"
        cat "$src"
        printf '\n'
      done
    else
      cat "$TMPBODY"
      printf '\n'
    fi
  } >> "$TRANSCRIPT"
  echo "Appended '$TITLE' to $(realpath --relative-to="$BRAIN" "$TRANSCRIPT")."
  # Append mode doesn't change validator-visible state; skip the rebuild for
  # speed. (The transcript is kind=transcript, which is exempt from V-06.)
  exit 0
fi

# ---------------------------------------------------------------------------
# 5. DEFAULT MODE — one or more separate files under the thread.
# ---------------------------------------------------------------------------
#
# Routing: *.md → threads/<slug>/artifacts/ (frontmatter injected).
#          Anything else → threads/<slug>/attachments/ (raw, no frontmatter).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE="${PACK_ROOT}/assets/artifact-template.md"
VERIFIER="${SCRIPT_DIR}/verify-tree.py"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "error: missing pack asset: $TEMPLATE" >&2
  exit 2
fi

ARTIFACTS_DIR="$THREAD_DIR/artifacts"
ATTACHMENTS_DIR="$THREAD_DIR/attachments"

# Next sequential number for artifacts/ (0001, 0002, ...).
next_artifact_n() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    printf '0001'
    return
  fi
  local max=0
  shopt -s nullglob
  for f in "$dir"/[0-9][0-9][0-9][0-9]-*.md; do
    local base; base="$(basename "$f")"
    local n="${base:0:4}"
    # strip leading zeros; fall back to 0 on anything unexpected
    n="${n#0}"; n="${n#0}"; n="${n#0}"
    [[ -z "$n" ]] && n=0
    if (( n > max )); then max=$n; fi
  done
  shopt -u nullglob
  printf '%04d' "$((max + 1))"
}

# Escape arbitrary text for safe insertion into sed (|-delimited).
escape_sed() { printf '%s' "$1" | sed 's|[|\\&]|\\&|g'; }

TITLE_E="$(escape_sed "$TITLE")"
BY_E="$(escape_sed "$BY")"
AKIND_E="$(escape_sed "$ARTIFACT_KIND")"
SLUG_E="$(escape_sed "$SLUG")"

# Build the list of (src, ext, body_path) triples we need to write. For
# --content/--stdin we use $TMPBODY as the body source and assume .md.
TARGETS=()
if [[ ${#FILES[@]} -gt 0 ]]; then
  for src in "${FILES[@]}"; do
    if [[ ! -f "$src" ]]; then
      echo "error: --file path not found: $src" >&2
      exit 2
    fi
    ext="${src##*.}"
    [[ "$ext" == "$src" ]] && ext=""
    TARGETS+=("${src}|${ext}")
  done
else
  TARGETS+=("${TMPBODY}|md")
fi

CREATED_PATHS=()

for entry in "${TARGETS[@]}"; do
  src="${entry%%|*}"
  ext="${entry##*|}"
  ext_lc="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"

  if [[ "$ext_lc" == "md" || "$ext_lc" == "markdown" ]]; then
    mkdir -p "$ARTIFACTS_DIR"
    N="$(next_artifact_n "$ARTIFACTS_DIR")"
    dest="$ARTIFACTS_DIR/${N}-${TITLE_SLUG}.md"
    id="${DATE_FOR_ID}/${SLUG}/artifact-${N}"

    # Template + substitutions + body injection. The template's {{BODY}}
    # marker is on its own line; we replace that whole line with the src
    # contents so we don't have to escape the body for sed.
    awk -v body_path="$src" '
      /^\{\{BODY\}\}$/ {
        while ((getline line < body_path) > 0) print line
        close(body_path)
        next
      }
      { print }
    ' "$TEMPLATE" | sed \
      -e "s|{{ID}}|${id}|g" \
      -e "s|{{TITLE}}|${TITLE_E}|g" \
      -e "s|{{CREATED_AT}}|${CREATED_AT}|g" \
      -e "s|{{CREATED_BY}}|${BY_E}|g" \
      -e "s|{{SLUG}}|${SLUG_E}|g" \
      -e "s|{{ARTIFACT_KIND}}|${AKIND_E}|g" \
      > "$dest"
    CREATED_PATHS+=("$dest")
  else
    mkdir -p "$ATTACHMENTS_DIR"
    base="$(basename "$src")"
    # If the source looks like a tempfile (tmp.* or a hex blob), rename to
    # something meaningful derived from --title + extension. Real uploads
    # with sensible names pass through unchanged.
    if [[ "$base" =~ ^tmp\. ]] || [[ "$base" =~ ^[a-zA-Z0-9]{10,}(\.[a-zA-Z0-9]+)?$ ]]; then
      if [[ -n "$ext" ]]; then
        base="${TITLE_SLUG}.${ext}"
      else
        base="${TITLE_SLUG}"
      fi
    fi
    # Preserve original filename but collision-safe.
    dest="$ATTACHMENTS_DIR/$base"
    if [[ -e "$dest" ]]; then
      stem="${base%.*}"
      suffix="${base##*.}"
      [[ "$suffix" == "$base" ]] && suffix=""
      i=2
      while [[ -e "$dest" ]]; do
        if [[ -n "$suffix" ]]; then
          dest="$ATTACHMENTS_DIR/${stem}-${i}.${suffix}"
        else
          dest="$ATTACHMENTS_DIR/${stem}-${i}"
        fi
        i=$((i+1))
      done
    fi
    cp "$src" "$dest"
    CREATED_PATHS+=("$dest")
  fi
done

# ---------------------------------------------------------------------------
# 6. Transcript breadcrumb — always, regardless of file type.
# ---------------------------------------------------------------------------

TRANSCRIPT="$THREAD_DIR/transcript.md"
touch "$TRANSCRIPT"
{
  printf '\n## %s — %s\n\n' "$CREATED_AT" "$TITLE"
  printf '_by %s · %s artifact%s._\n\n' \
    "$BY" "$ARTIFACT_KIND" "$( [[ ${#CREATED_PATHS[@]} -gt 1 ]] && printf 's' )"
  for p in "${CREATED_PATHS[@]}"; do
    rel="$(realpath --relative-to="$THREAD_DIR" "$p")"
    printf -- '- → %s\n' "$rel"
  done
} >> "$TRANSCRIPT"

# ---------------------------------------------------------------------------
# 7. Rebuild aggregate indexes + post-write validation.
# ---------------------------------------------------------------------------

if [[ $NO_REBUILD -eq 0 && -f "$VERIFIER" ]]; then
  if ! python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index > /dev/null 2>&1; then
    # Rebuild failed — but the artifact(s) are on disk. Tell the user how
    # to diagnose. Exit 1 to signal the brain isn't clean, though the
    # capture itself succeeded.
    echo "warning: post-write rebuild reported problems. The artifact(s) are saved;" >&2
    echo "         run 'verify-tree --brain $BRAIN' to see specifics." >&2
    echo "created:" >&2
    for p in "${CREATED_PATHS[@]}"; do
      echo "  $(realpath --relative-to="$BRAIN" "$p")" >&2
    done
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# 8. Report.
# ---------------------------------------------------------------------------

if [[ ${#CREATED_PATHS[@]} -eq 1 ]]; then
  echo "Recorded artifact: $(realpath --relative-to="$BRAIN" "${CREATED_PATHS[0]}")."
else
  echo "Recorded ${#CREATED_PATHS[@]} artifacts under thread '$SLUG':"
  for p in "${CREATED_PATHS[@]}"; do
    echo "  $(realpath --relative-to="$BRAIN" "$p")"
  done
fi
if [[ "$BY" == "TODO@example.com" ]]; then
  echo "  by = TODO@example.com placeholder; pass --by=<email> to replace."
fi

exit 0
