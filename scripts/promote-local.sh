#!/usr/bin/env bash
# promote-local.sh — promote staged leaves from a thread into tree/ WITHOUT a
# branch, push, or PR. This is the `--mode=local` implementation from
# CONVENTIONS § 4 (promotion modes).
#
# Assumes the leaves have already been staged at
# `threads/<slug>/tree-staging/<domain>/<leaf-slug>.md`. That staging step is
# a separate responsibility (handled by the `promote-thread-to-tree` skill's
# pre-landing flow, or set up manually). This script takes the staged files
# and LANDS them — moves to tree/, updates NODE.md, flips statuses, rebuilds
# indexes. No git orchestration; optionally commits locally if a git repo is
# present and no `--no-commit` flag is set.
#
# Usage:
#   scripts/promote-local.sh \
#       --brain=<path>                \
#       --slug=<thread-slug>          \
#       [--leaves=<csv>]              \  # defaults to all staged leaves
#       [--no-commit]                 \  # skip local git commit even if repo present
#       [--archive-thread]            \  # also move thread to archive/ (all leaves promoted)
#       [--by=<email>]                   # actor email; default TODO@example.com
#
# Exit codes:
#   0   promotion landed cleanly
#   1   operational failure (no staged leaves, rebuild failed, etc.)
#   2   invocation error

set -euo pipefail

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------

BRAIN=""
SLUG=""
LEAVES_CSV=""
NO_COMMIT=0
ARCHIVE_THREAD=0
BY="TODO@example.com"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)         BRAIN="${1#*=}"; shift ;;
    --brain)           BRAIN="$2"; shift 2 ;;
    --slug=*)          SLUG="${1#*=}"; shift ;;
    --slug)            SLUG="$2"; shift 2 ;;
    --leaves=*)        LEAVES_CSV="${1#*=}"; shift ;;
    --leaves)          LEAVES_CSV="$2"; shift 2 ;;
    --no-commit)       NO_COMMIT=1; shift ;;
    --archive-thread)  ARCHIVE_THREAD=1; shift ;;
    --by=*)            BY="${1#*=}"; shift ;;
    --by)              BY="$2"; shift 2 ;;
    -h|--help)         head -n 30 "$0"; exit 0 ;;
    *)                 echo "error: unknown arg: $1" >&2; exit 2 ;;
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
if [[ ! -f "$BRAIN/CONVENTIONS.md" ]]; then
  echo "error: $BRAIN is not a project-brain (missing CONVENTIONS.md)." >&2
  exit 2
fi

THREAD_DIR="$BRAIN/threads/$SLUG"
if [[ ! -d "$THREAD_DIR" ]]; then
  echo "error: thread not found at $THREAD_DIR" >&2
  exit 2
fi
STAGING_DIR="$THREAD_DIR/tree-staging"
if [[ ! -d "$STAGING_DIR" ]]; then
  echo "error: no staged leaves at $STAGING_DIR" >&2
  echo "       Stage leaves first (via the promote-thread-to-tree skill's" >&2
  echo "       staging step, or manually copy leaf-template.md files into" >&2
  echo "       threads/<slug>/tree-staging/<domain>/<leaf>.md)." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Enumerate staged leaves (optionally filtered by --leaves)
# ---------------------------------------------------------------------------

# Build an array of "domain|leaf-slug|staged-path" triples.
STAGED=()
while IFS= read -r f; do
  # f is relative to STAGING_DIR, e.g., "architecture/transport-choice.md"
  [[ -z "$f" ]] && continue
  domain="$(dirname "$f")"
  leaf_file="$(basename "$f")"
  leaf_slug="${leaf_file%.md}"
  STAGED+=("${domain}|${leaf_slug}|${STAGING_DIR}/${f}")
done < <(cd "$STAGING_DIR" && find . -mindepth 2 -type f -name '*.md' 2>/dev/null | sed 's|^\./||' | sort)

if [[ ${#STAGED[@]} -eq 0 ]]; then
  echo "error: no staged leaves found under $STAGING_DIR" >&2
  exit 1
fi

# Apply --leaves filter if supplied.
if [[ -n "$LEAVES_CSV" ]]; then
  # split CSV into a set
  declare -A WANTED=()
  IFS=',' read -r -a wanted_arr <<< "$LEAVES_CSV"
  for w in "${wanted_arr[@]}"; do
    w="$(printf '%s' "$w" | sed 's/^ *//;s/ *$//')"
    [[ -n "$w" ]] && WANTED["$w"]=1
  done
  FILTERED=()
  for entry in "${STAGED[@]}"; do
    slug="$(echo "$entry" | cut -d'|' -f2)"
    if [[ -n "${WANTED[$slug]:-}" ]]; then
      FILTERED+=("$entry")
    fi
  done
  if [[ ${#FILTERED[@]} -eq 0 ]]; then
    echo "error: --leaves='$LEAVES_CSV' matched none of the staged leaves." >&2
    echo "       staged:" >&2
    for e in "${STAGED[@]}"; do echo "         $(echo "$e" | cut -d'|' -f2)" >&2; done
    exit 1
  fi
  STAGED=("${FILTERED[@]}")
fi

# ---------------------------------------------------------------------------
# Land leaves: staging → tree/
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NODE_TEMPLATE="${PACK_ROOT}/assets/NODE-template.md"
VERIFIER="${SCRIPT_DIR}/verify-tree.py"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LANDED_PATHS=()   # tree-relative paths of landed leaves, for promoted_to

for entry in "${STAGED[@]}"; do
  domain="$(echo "$entry" | cut -d'|' -f1)"
  leaf_slug="$(echo "$entry" | cut -d'|' -f2)"
  staged_path="$(echo "$entry" | cut -d'|' -f3)"

  # Refuse if target already exists.
  target_dir="${BRAIN}/tree/${domain}"
  target_file="${target_dir}/${leaf_slug}.md"
  if [[ -e "$target_file" ]]; then
    echo "error: target already exists: tree/${domain}/${leaf_slug}.md" >&2
    echo "       (did you mean to update the existing leaf rather than re-promote?)" >&2
    exit 1
  fi

  mkdir -p "$target_dir"

  # Copy + flip leaf status draft → decided (local mode commits directly).
  # Use sed to replace status line in the frontmatter.
  sed 's/^status: draft$/status: decided/' "$staged_path" > "$target_file"

  # NODE.md: create if missing, then append the leaf.
  node_md="${target_dir}/NODE.md"
  if [[ ! -f "$node_md" ]]; then
    # Instantiate from template.
    node_id="$(printf '%s' "$domain" | sed 's|/|-|g')-node"
    node_title="$(printf '%s' "$domain" | sed -e 's|/| · |g' -e 's/-/ /g' -e 's/\b./\U&/g')"
    primary_project="$(awk '/^primary_project[[:space:]]*:/ { sub(/^primary_project[[:space:]]*:[[:space:]]*/, ""); gsub(/["\x27]/, ""); print; exit }' "$BRAIN/config.yaml" 2>/dev/null || echo project)"
    sed -e "s|{{NODE_ID}}|${node_id}|g" \
        -e "s|{{NODE_TITLE}}|${node_title}|g" \
        -e "s|{{CREATED_AT}}|${NOW}|g" \
        -e "s|{{OWNER}}|${BY}|g" \
        -e "s|{{PRIMARY_PROJECT}}|${primary_project}|g" \
        -e "s|{{NODE_DOMAIN}}|${domain}|g" \
        "$NODE_TEMPLATE" > "$node_md"
    # Strip HTML-commented placeholder bullets — the validator parses
    # bullet-shaped lines inside HTML comments as real links and reports
    # unresolved references (`./leaf-slug.md`). Remove them at scaffold time.
    sed -i.bak '/^<!-- - \[/d' "$node_md" && rm -f "${node_md}.bak" 2>/dev/null || true
  fi

  # Extract the leaf's H1 title for the NODE.md bullet.
  leaf_title="$(awk '/^# /{sub(/^# +/, ""); print; exit}' "$target_file")"
  [[ -z "$leaf_title" ]] && leaf_title="$leaf_slug"

  # Append a bullet under "## Leaves". Use awk so we find the right section
  # and insert just below it (before any trailing blank line or next H2).
  bullet="- [${leaf_title}](./${leaf_slug}.md)"
  python3 - "$node_md" "$bullet" <<'PY'
# Line-based insert: find "## Leaves" header, append bullet at the END of
# that section (before the next "## " header or EOF). Idempotent — does
# nothing if the bullet is already present anywhere in the Leaves section.
import sys
path, bullet = sys.argv[1], sys.argv[2]
lines = open(path).read().splitlines()

# Locate start + end of the ## Leaves section.
start = end = None
for i, L in enumerate(lines):
    if L.startswith("## Leaves"):
        start = i + 1
        for j in range(start, len(lines)):
            if lines[j].startswith("## "):
                end = j
                break
        if end is None:
            end = len(lines)
        break

if start is None:
    # No Leaves section — append one at EOF.
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend(["## Leaves", "", bullet, ""])
else:
    section = lines[start:end]
    # Idempotence: already present?
    if any(bullet in L for L in section):
        pass
    else:
        # Trim trailing blank lines from the section, append the bullet,
        # then re-add exactly one trailing blank before the next header.
        trimmed = list(section)
        while trimmed and not trimmed[-1].strip():
            trimmed.pop()
        trimmed.append(bullet)
        trimmed.append("")
        lines[start:end] = trimmed

open(path, "w").write("\n".join(lines) + "\n")
PY

  LANDED_PATHS+=("tree/${domain}/${leaf_slug}.md")
  rm -f "$staged_path"
done

# Clean up empty tree-staging/<domain>/ dirs.
find "$STAGING_DIR" -mindepth 1 -type d -empty -delete 2>/dev/null || true
# Clean up tree-staging/ itself if fully empty.
rmdir "$STAGING_DIR" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Update thread frontmatter: promoted_to, promoted_at, maturity
# ---------------------------------------------------------------------------

THREAD_MD="$THREAD_DIR/thread.md"
python3 - "$THREAD_MD" "$NOW" "${LANDED_PATHS[@]}" <<'PY'
import sys, re
path = sys.argv[1]
now = sys.argv[2]
landed = sys.argv[3:]

try:
    import yaml
except ImportError:
    print("error: PyYAML required for thread frontmatter update.", file=sys.stderr)
    sys.exit(1)

text = open(path).read()
m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
if not m:
    print(f"error: no frontmatter in {path}", file=sys.stderr)
    sys.exit(1)

fm = yaml.safe_load(m.group(1)) or {}
body = m.group(2)

# Append landed leaves to promoted_to + matching timestamps to promoted_at.
promoted_to = fm.get("promoted_to") or []
promoted_at = fm.get("promoted_at") or []
for p in landed:
    promoted_to.append(p)
    promoted_at.append(now)
fm["promoted_to"] = promoted_to
fm["promoted_at"] = promoted_at

# Bump maturity to locking if currently exploring/refining.
mat = fm.get("maturity")
if mat in ("exploring", "refining"):
    fm["maturity"] = "locking"

# last_modified_*
fm["last_modified_at"] = now
# Preserve created_by/owner fields unchanged.

new_fm = yaml.safe_dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
open(path, "w").write(f"---\n{new_fm}---\n{body}")
PY

# ---------------------------------------------------------------------------
# Optionally archive the thread (--archive-thread)
# ---------------------------------------------------------------------------

THREAD_FINAL_DIR="$THREAD_DIR"
if [[ $ARCHIVE_THREAD -eq 1 ]]; then
  ARCHIVE_DEST="$BRAIN/archive/$SLUG"
  if [[ -e "$ARCHIVE_DEST" ]]; then
    echo "warning: archive/$SLUG/ already exists; skipping archive move." >&2
  else
    mkdir -p "$BRAIN/archive"
    mv "$THREAD_DIR" "$ARCHIVE_DEST"
    THREAD_FINAL_DIR="$ARCHIVE_DEST"
    # Flip status → archived in frontmatter.
    python3 - "$ARCHIVE_DEST/thread.md" "$NOW" "$BY" <<'PY'
import sys, re, yaml
path, now, by = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()
m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
fm = yaml.safe_load(m.group(1)) or {}
fm["status"] = "archived"
fm.pop("maturity", None)
fm["archived_at"] = now
fm["archived_by"] = by
new_fm = yaml.safe_dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
open(path, "w").write(f"---\n{new_fm}---\n{m.group(2)}")
PY
  fi
fi

# ---------------------------------------------------------------------------
# Rebuild aggregate indexes
# ---------------------------------------------------------------------------

if [[ -f "$VERIFIER" ]]; then
  if ! python3 "$VERIFIER" --brain "$BRAIN" --rebuild-index > /dev/null 2>&1; then
    echo "warning: post-promotion rebuild reported problems." >&2
    echo "         Leaves are on disk; run 'verify-tree --brain $BRAIN' to diagnose." >&2
  fi
fi

# ---------------------------------------------------------------------------
# Optional local git commit
# ---------------------------------------------------------------------------

DID_COMMIT=0
if [[ $NO_COMMIT -eq 0 ]]; then
  # Walk up from BRAIN to find a git repo root.
  cur="$BRAIN"
  git_root=""
  for _ in $(seq 1 10); do
    if [[ -e "$cur/.git" ]]; then git_root="$cur"; break; fi
    parent="$(dirname "$cur")"
    [[ "$parent" == "$cur" ]] && break
    cur="$parent"
  done
  if [[ -n "$git_root" ]] && command -v git >/dev/null 2>&1; then
    cd "$git_root"
    git add "$BRAIN/tree/" "$BRAIN/threads/" "$BRAIN/archive/" \
            "$BRAIN/thread-index.md" "$BRAIN/current-state.md" 2>/dev/null || true
    if ! git diff --cached --quiet 2>/dev/null; then
      git commit --quiet -m "promote($SLUG): land ${#LANDED_PATHS[@]} leaves (local mode)" || true
      DID_COMMIT=1
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

echo "Promoted ${#LANDED_PATHS[@]} leaves from thread '$SLUG' to tree/ (mode=local)."
for p in "${LANDED_PATHS[@]}"; do echo "  → $p"; done
if [[ $ARCHIVE_THREAD -eq 1 && "$THREAD_FINAL_DIR" == "$BRAIN/archive/$SLUG" ]]; then
  echo "  thread archived to archive/$SLUG/"
fi
if [[ $DID_COMMIT -eq 1 ]]; then
  echo "  committed locally (branch: $(git -C "$BRAIN" symbolic-ref --short HEAD 2>/dev/null || echo '?'))"
fi
echo "Done."

exit 0
