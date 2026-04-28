#!/usr/bin/env bash
# review-thread.sh — one-shot thread review.
#
# Prints a read-only summary of a thread to stdout:
#   - thread frontmatter (slug, status/maturity, dates, assigned_to, purpose)
#   - open questions (count + one-line preview each)
#   - decisions-candidates (counts by status + one-line preview each)
#   - artifacts (one line each: path, title, artifact_kind)
#   - transcript: count + last 3 entries (default), or full dump with --full
#
# Pure read-only — no writes, no shell spawns beyond standard coreutils + awk.
# Single permission prompt in an agent UI. ~120ms on a medium thread.
#
# Usage:
#   scripts/review-thread.sh \
#       --brain=<path>              \  # absolute path to brain
#       --slug=<slug>               \  # thread to review (must exist in threads/ or archive/)
#       [--full]                    \  # also dump the full transcript
#       [--last=<N>]                \  # transcript: last N entries (default: 3; ignored with --full)
#       [--since=<ISO8601>]         \  # transcript: entries on or after this timestamp
#
# Exit codes:
#   0   summary printed
#   2   invocation error (bad args, thread not found, brain invalid)

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
FULL=0
LAST=3
SINCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)   BRAIN="${1#*=}"; shift ;;
    --brain)     BRAIN="$2"; shift 2 ;;
    --slug=*)    SLUG="${1#*=}"; shift ;;
    --slug)      SLUG="$2"; shift 2 ;;
    --full)      FULL=1; shift ;;
    --last=*)    LAST="${1#*=}"; shift ;;
    --last)      LAST="$2"; shift 2 ;;
    --since=*)   SINCE="${1#*=}"; shift ;;
    --since)     SINCE="$2"; shift 2 ;;
    -h|--help)   head -n 25 "$0"; exit 0 ;;
    *)           echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

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

THREAD_DIR=""
LOCATION=""
for loc in threads archive; do
  if [[ -d "$BRAIN/$loc/$SLUG" ]]; then
    THREAD_DIR="$BRAIN/$loc/$SLUG"
    LOCATION="$loc"
    break
  fi
done
if [[ -z "$THREAD_DIR" ]]; then
  echo "error: thread '$SLUG' not found in $BRAIN/threads/ or $BRAIN/archive/." >&2
  exit 2
fi

THREAD_MD="$THREAD_DIR/thread.md"
if [[ ! -f "$THREAD_MD" ]]; then
  echo "error: $THREAD_MD does not exist (thread directory is malformed)." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 2. Extract frontmatter scalar fields via awk. The pack's YAML is a narrow
#    subset (flat scalars + one-level lists); we don't need PyYAML here.
# ---------------------------------------------------------------------------

fm_scalar() {
  # $1 = file, $2 = field name → print first matching scalar value or empty
  awk -v field="$2" '
    BEGIN { in_fm=0; done=0 }
    /^---[[:space:]]*$/ { in_fm = !in_fm; if (!in_fm) exit; next }
    in_fm && $0 ~ "^" field "[[:space:]]*:" {
      sub("^" field "[[:space:]]*:[[:space:]]*", "", $0)
      gsub(/^["\x27]|["\x27][[:space:]]*$/, "", $0)
      print; exit
    }
  ' "$1"
}

fm_list() {
  # $1 = file, $2 = field name → print inline flow list OR block list items
  awk -v field="$2" '
    BEGIN { in_fm=0; in_list=0 }
    /^---[[:space:]]*$/ { in_fm = !in_fm; if (!in_fm) exit; next }
    in_fm {
      if ($0 ~ "^" field "[[:space:]]*:[[:space:]]*\\[") {
        # Inline flow list: extract between [ and ]
        line = $0
        sub(".*\\[", "", line); sub("\\].*", "", line)
        if (length(line) == 0) exit
        n = split(line, items, ",")
        for (i=1; i<=n; i++) {
          v = items[i]
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
          gsub(/^["\x27]|["\x27]$/, "", v)
          if (length(v) > 0) print v
        }
        exit
      }
      if ($0 ~ "^" field "[[:space:]]*:[[:space:]]*$") { in_list=1; next }
      if (in_list) {
        if ($0 ~ /^[[:space:]]*-[[:space:]]/) {
          v = $0
          sub(/^[[:space:]]*-[[:space:]]+/, "", v)
          gsub(/^["\x27]|["\x27]$/, "", v)
          print v
        } else if ($0 ~ /^[^[:space:]]/) {
          in_list=0
        }
      }
    }
  ' "$1"
}

STATUS="$(fm_scalar "$THREAD_MD" status)"
MATURITY="$(fm_scalar "$THREAD_MD" maturity)"
CREATED_AT="$(fm_scalar "$THREAD_MD" created_at)"
CREATED_BY="$(fm_scalar "$THREAD_MD" created_by)"
LAST_MOD_AT="$(fm_scalar "$THREAD_MD" last_modified_at)"
LAST_MOD_BY="$(fm_scalar "$THREAD_MD" last_modified_by)"
OWNER="$(fm_scalar "$THREAD_MD" owner)"
PRIMARY_PROJECT="$(fm_scalar "$THREAD_MD" primary_project)"
TITLE="$(fm_scalar "$THREAD_MD" title)"
PURPOSE="$(fm_scalar "$THREAD_MD" purpose)"

# First H1 for title fallback
if [[ -z "$TITLE" ]]; then
  TITLE="$(awk '/^#[[:space:]]+/ { sub(/^#[[:space:]]+/, ""); print; exit }' "$THREAD_MD")"
fi

ASSIGNED_TO=()
while IFS= read -r line; do
  [[ -n "$line" ]] && ASSIGNED_TO+=("$line")
done < <(fm_list "$THREAD_MD" assigned_to)

# ---------------------------------------------------------------------------
# 3. Scan open-questions.md + decisions-candidates.md (best-effort — these
#    are freeform markdown, we just count top-level list items).
# ---------------------------------------------------------------------------

count_top_list_items() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo 0
    return
  fi
  # Skip frontmatter if present; count lines matching "- " or "* " at column 0.
  awk '
    BEGIN { in_fm=0; past_fm=0 }
    NR==1 && /^---/ { in_fm=1; next }
    in_fm && /^---/ { in_fm=0; past_fm=1; next }
    in_fm { next }
    /^[-*][[:space:]]/ { c++ }
    END { print c+0 }
  ' "$f"
}

OQ_COUNT="$(count_top_list_items "$THREAD_DIR/open-questions.md")"
DC_COUNT="$(count_top_list_items "$THREAD_DIR/decisions-candidates.md")"

# ---------------------------------------------------------------------------
# 4. Enumerate artifacts + attachments.
# ---------------------------------------------------------------------------

ARTIFACTS=()
if [[ -d "$THREAD_DIR/artifacts" ]]; then
  while IFS= read -r f; do
    [[ -n "$f" ]] && ARTIFACTS+=("$f")
  done < <(find "$THREAD_DIR/artifacts" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort)
fi

ATTACHMENTS=()
if [[ -d "$THREAD_DIR/attachments" ]]; then
  while IFS= read -r f; do
    [[ -n "$f" ]] && ATTACHMENTS+=("$f")
  done < <(find "$THREAD_DIR/attachments" -maxdepth 1 -type f 2>/dev/null | sort)
fi

# Format bytes → human-readable string ("420 B", "12.3 KB", "4.5 MB").
human_size() {
  local b="${1:-?}"
  if [[ "$b" == "?" || -z "$b" ]]; then echo "?"; return; fi
  awk -v b="$b" 'BEGIN {
    if (b < 1024)              printf "%d B",   b;
    else if (b < 1048576)      printf "%.1f KB", b/1024;
    else if (b < 1073741824)   printf "%.1f MB", b/1048576;
    else                       printf "%.1f GB", b/1073741824;
  }'
}

# ---------------------------------------------------------------------------
# 5. Transcript: count H2 entries + extract recent ones.
# ---------------------------------------------------------------------------

TRANSCRIPT="$THREAD_DIR/transcript.md"
TRANSCRIPT_COUNT=0
TRANSCRIPT_LAST_TS=""
if [[ -f "$TRANSCRIPT" ]]; then
  TRANSCRIPT_COUNT="$(awk '/^## / { c++ } END { print c+0 }' "$TRANSCRIPT")"
  TRANSCRIPT_LAST_TS="$(awk '/^## [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ {
    line = $0
    sub(/^## /, "", line)
    split(line, parts, " — ")
    ts = parts[1]
  }
  END { print ts }' "$TRANSCRIPT")"
fi

# ---------------------------------------------------------------------------
# 6. Render the summary.
# ---------------------------------------------------------------------------

printf '# Thread: %s\n' "$SLUG"
printf '  location:     %s/%s/\n' "$LOCATION" "$SLUG"
[[ -n "$TITLE" ]]           && printf '  title:        %s\n' "$TITLE"
[[ -n "$STATUS" ]]          && printf '  status:       %s' "$STATUS"
[[ -n "$MATURITY" ]]        && printf ' / %s' "$MATURITY"
[[ -n "$STATUS" ]]          && printf '\n'
[[ -n "$PRIMARY_PROJECT" ]] && printf '  project:      %s\n' "$PRIMARY_PROJECT"
[[ -n "$OWNER" ]]           && printf '  owner:        %s\n' "$OWNER"
if [[ ${#ASSIGNED_TO[@]} -gt 0 ]]; then
  printf '  assigned_to:  %s\n' "$(IFS=,; echo "${ASSIGNED_TO[*]}")"
fi
[[ -n "$CREATED_AT" ]]   && printf '  created:      %s%s\n' \
  "$CREATED_AT" "$( [[ -n "$CREATED_BY" ]] && printf ' by %s' "$CREATED_BY" )"
[[ -n "$LAST_MOD_AT" ]]  && printf '  last_mod:     %s%s\n' \
  "$LAST_MOD_AT" "$( [[ -n "$LAST_MOD_BY" ]] && printf ' by %s' "$LAST_MOD_BY" )"
[[ -n "$PURPOSE" ]]      && printf '  purpose:      %s\n' "$PURPOSE"

# --------------------------------------------------------------------------
# thread.md body — extract everything after the closing frontmatter delim.
# Threads commonly carry their substantive content here (per CONVENTIONS:
# "thread.md = frontmatter + freeform notes"); review-thread previously
# only read frontmatter scalars and rendered transcript+artifacts, leaving
# threads with body-only content looking nearly empty.
# --------------------------------------------------------------------------
extract_body() {
  awk 'BEGIN{c=0} /^---[[:space:]]*$/ && c<2 {c++; next} c>=2 {print}' "$1"
}
BODY="$(extract_body "$THREAD_MD")"
BODY_LINE_COUNT=$(printf '%s' "$BODY" | grep -c .)

OQ_FILE="$THREAD_DIR/open-questions.md"
DC_FILE="$THREAD_DIR/decisions-candidates.md"

printf '\n'
printf '  open questions:        %s\n' "$OQ_COUNT"
printf '  decisions-candidates:  %s\n' "$DC_COUNT"
printf '  artifacts:             %s\n' "${#ARTIFACTS[@]}"
printf '  attachments:           %s\n' "${#ATTACHMENTS[@]}"
printf '  body lines:            %s\n' "$BODY_LINE_COUNT"
printf '  transcript entries:    %s' "$TRANSCRIPT_COUNT"
[[ -n "$TRANSCRIPT_LAST_TS" ]] && printf ' (last at %s)' "$TRANSCRIPT_LAST_TS"
printf '\n'

# --------------------------------------------------------------------------
# Files block — clickable computer:// links for every file the user is
# likely to want to open directly. This is the default detail view: the
# script can't show *everything*, but it can hand the user a one-click path
# into each file. The earlier default ("body present, use --full") buried
# the user's data; this surfaces it instead.
# --------------------------------------------------------------------------
emit_link() {
  # $1 = label, $2 = absolute path, $3 = trailing annotation (optional)
  local label="$1" abs="$2" annot="${3:-}"
  if [[ -n "$annot" ]]; then
    printf '  [%s](computer://%s) — %s\n' "$label" "$abs" "$annot"
  else
    printf '  [%s](computer://%s)\n' "$label" "$abs"
  fi
}

printf '\nFiles:\n'
emit_link "thread.md" "$THREAD_MD" \
  "$( [[ $BODY_LINE_COUNT -gt 0 ]] && printf '%s body lines' "$BODY_LINE_COUNT" || printf 'frontmatter only' )"
if [[ -f "$OQ_FILE" ]]; then
  emit_link "open-questions.md" "$OQ_FILE" "$OQ_COUNT items"
fi
if [[ -f "$DC_FILE" ]]; then
  emit_link "decisions-candidates.md" "$DC_FILE" "$DC_COUNT items"
fi
if [[ -f "$TRANSCRIPT" ]]; then
  if [[ -n "$TRANSCRIPT_LAST_TS" ]]; then
    emit_link "transcript.md" "$TRANSCRIPT" "$TRANSCRIPT_COUNT entries, last $TRANSCRIPT_LAST_TS"
  else
    emit_link "transcript.md" "$TRANSCRIPT" "$TRANSCRIPT_COUNT entries"
  fi
fi

if [[ ${#ARTIFACTS[@]} -gt 0 ]]; then
  printf '\nArtifacts (%s):\n' "${#ARTIFACTS[@]}"
  for p in "${ARTIFACTS[@]}"; do
    atitle="$(fm_scalar "$p" title)"
    akind="$(fm_scalar "$p" artifact_kind)"
    [[ -z "$akind" ]] && akind="-"
    [[ -z "$atitle" ]] && atitle="$(basename "$p" .md)"
    rel="$(realpath --relative-to="$THREAD_DIR" "$p")"
    printf '  [%s](computer://%s) — [%s] %s\n' "$rel" "$p" "$akind" "$atitle"
  done
fi

if [[ ${#ATTACHMENTS[@]} -gt 0 ]]; then
  printf '\nAttachments (%s):\n' "${#ATTACHMENTS[@]}"
  for p in "${ATTACHMENTS[@]}"; do
    rel="$(realpath --relative-to="$THREAD_DIR" "$p")"
    size_b="$(stat -c%s "$p" 2>/dev/null || stat -f%z "$p" 2>/dev/null || echo '?')"
    size_h="$(human_size "$size_b")"
    printf '  [%s](computer://%s) — %s\n' "$rel" "$p" "$size_h"
  done
fi

# --------------------------------------------------------------------------
# Body rendering. --full dumps the entire body verbatim. Default mode is
# silent here — the Files block above already surfaced the link plus line
# count, so an extra "body present" hint would be redundant.
# --------------------------------------------------------------------------
if [[ $FULL -eq 1 && $BODY_LINE_COUNT -gt 0 ]]; then
  printf '\n----- thread.md body -----\n'
  printf '%s\n' "$BODY"
fi

if [[ $TRANSCRIPT_COUNT -eq 0 ]]; then
  exit 0
fi

# Transcript rendering:
#  --full   → dump entire file verbatim (prefixed with a marker line)
#  default  → last $LAST entries, filtered by --since
render_transcript() {
  if [[ $FULL -eq 1 ]]; then
    printf '\n----- transcript.md (full) -----\n'
    cat "$TRANSCRIPT"
    return
  fi
  # Emit entries (each is an H2 block + its body until the next H2 or EOF).
  # First pass: collect entries with their timestamps. Second pass: filter +
  # slice. Implemented in awk for single-pass portability.
  awk -v last="$LAST" -v since="$SINCE" '
    function flush(block, ts,    out) {
      # Append to an array indexed by insertion order.
      n_entries++
      entries[n_entries] = block
      timestamps[n_entries] = ts
    }
    BEGIN { block = ""; ts = ""; seen_header = 0 }
    /^## / {
      if (seen_header) flush(block, ts)
      block = $0 "\n"
      seen_header = 1
      line = $0; sub(/^## /, "", line); split(line, parts, " — ")
      ts = parts[1]
      next
    }
    # Ignore all lines before the first "## " header — leading newline from
    # our own appender would otherwise become a phantom entry 1.
    seen_header { block = block $0 "\n" }
    END {
      if (seen_header) flush(block, ts)
      start = 1
      if (!last) last = 3
      if (since == "") {
        start = n_entries - last + 1
        if (start < 1) start = 1
      } else {
        for (i=1; i<=n_entries; i++) {
          if (timestamps[i] >= since) { start = i; break }
          if (i == n_entries) start = n_entries + 1
        }
        # Also apply --last on top of --since
        if (n_entries - start + 1 > last) start = n_entries - last + 1
      }
      if (start > n_entries) {
        print "  (no transcript entries match --since=" since ")"
        exit
      }
      printf "\n----- transcript.md (entries %d–%d of %d) -----\n", \
        start, n_entries, n_entries
      for (i=start; i<=n_entries; i++) printf "%s", entries[i]
    }
  ' "$TRANSCRIPT"
}

render_transcript

exit 0
