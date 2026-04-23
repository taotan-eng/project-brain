#!/usr/bin/env bash
# init-brain.sh — one-shot project-brain scaffold.
#
# This script replaces ~8 individual file-tool calls with a single bash
# invocation. Target runtime: well under 1 second for a fresh scaffold.
# Inside an agentic IDE, the user sees ONE permission prompt (for this
# script) instead of many (for each Write / mkdir individually).
#
# Templates are copied from the pack's shipped `assets/` directory,
# which lives alongside this script's own parent (`scripts/../assets/`).
# Nothing is read from or written to `~/` except — optionally — the
# user-global registry at `~/.config/project-brain/projects.yaml`,
# which is the SINGLE thing that legitimately lives there per CONVENTIONS
# § 2. This script never writes anywhere else under the user's home dir.
#
# Usage:
#   scripts/init-brain.sh \
#       --home=<path>         \  # project home dir (brain goes inside here)
#       --alias=<slug>        \  # project alias (kebab-case)
#       --title=<title>       \  # human-readable title
#       [--owner=<email>]     \  # owner email; default: TODO@example.com
#       [--domain=<slug>]     \  # optional initial tree domain (rare — most
#                                #   projects let promote-thread-to-tree create
#                                #   domains on demand).
#       [--init-git]          \  # run git init + single bootstrap commit
#       [--with-registry]     \  # append an entry to ~/.config/project-brain/projects.yaml
#       [--force]             \  # if a brain already exists at <home>/project-brain/,
#                                #   back it up to project-brain.bak.<ts>/ and scaffold fresh
#
# Exit codes:
#   0   scaffold complete
#   1   refused: existing brain without --force
#   2   invocation error (bad args, unreadable templates, etc.)
#
# Notes:
# - Pure bash + standard POSIX utilities (mkdir, cp, sed, date). No jq,
#   no python — so the init step has zero Python-runtime preconditions.
# - Errors land on stderr. Stdout is strictly terse: one success line.

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse args
# ---------------------------------------------------------------------------

PROJECT_HOME=""
PROJECT_ALIAS=""
PROJECT_TITLE=""
OWNER="TODO@example.com"
OWNER_SOURCE="placeholder"
DOMAIN=""
INIT_GIT=0
WITH_REGISTRY=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --home=*)          PROJECT_HOME="${1#*=}"; shift ;;
    --home)            PROJECT_HOME="$2"; shift 2 ;;
    --alias=*)         PROJECT_ALIAS="${1#*=}"; shift ;;
    --alias)           PROJECT_ALIAS="$2"; shift 2 ;;
    --title=*)         PROJECT_TITLE="${1#*=}"; shift ;;
    --title)           PROJECT_TITLE="$2"; shift 2 ;;
    --owner=*)         OWNER="${1#*=}"; OWNER_SOURCE="flag"; shift ;;
    --owner)           OWNER="$2"; OWNER_SOURCE="flag"; shift 2 ;;
    --domain=*)        DOMAIN="${1#*=}"; shift ;;
    --domain)          DOMAIN="$2"; shift 2 ;;
    --init-git)        INIT_GIT=1; shift ;;
    --with-registry)   WITH_REGISTRY=1; shift ;;
    --force)           FORCE=1; shift ;;
    -h|--help)         head -n 40 "$0"; exit 0 ;;
    *)                 echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# 2. Auto-detect missing inputs (so the LLM never has to invoke Python
#    just to determine where the host project lives)
# ---------------------------------------------------------------------------
#
# CONVENTIONS § 1 commits to a 1:1 correspondence between a project-brain
# project and the host environment's project concept. We probe the same
# priority chain `detect_host_project_root()` uses, but in pure bash so
# nothing can wedge on a missing Python/PyYAML setup.

HOME_SOURCE=""
if [[ -z "$PROJECT_HOME" ]]; then
  if [[ -n "${PROJECT_BRAIN_HOME:-}" ]]; then
    PROJECT_HOME="$PROJECT_BRAIN_HOME";  HOME_SOURCE="env:PROJECT_BRAIN_HOME"
  elif [[ -n "${COWORK_WORKSPACE_FOLDER:-}" ]]; then
    PROJECT_HOME="$COWORK_WORKSPACE_FOLDER"; HOME_SOURCE="cowork-workspace"
  elif [[ -n "${CODEX_PROJECT_ROOT:-}" ]]; then
    PROJECT_HOME="$CODEX_PROJECT_ROOT";  HOME_SOURCE="codex-project"
  elif [[ -n "${CLAUDE_PROJECT_ROOT:-}" ]]; then
    PROJECT_HOME="$CLAUDE_PROJECT_ROOT"; HOME_SOURCE="claude-project"
  else
    # Walk up for .git; bail at filesystem root.
    CURSOR="$(pwd -P)"
    for _ in $(seq 1 40); do
      if [[ -e "$CURSOR/.git" ]]; then
        PROJECT_HOME="$CURSOR"; HOME_SOURCE="git-root"; break
      fi
      PARENT="$(dirname "$CURSOR")"
      if [[ "$PARENT" == "$CURSOR" ]]; then break; fi
      CURSOR="$PARENT"
    done
    if [[ -z "$PROJECT_HOME" ]]; then
      PROJECT_HOME="$(pwd -P)"; HOME_SOURCE="cwd"
    fi
  fi
fi

# Resolve to absolute path; refuse if doesn't exist (we don't create
# arbitrary parent dirs — that's a host-level responsibility).
if [[ ! -d "$PROJECT_HOME" ]]; then
  echo "error: project home does not exist: $PROJECT_HOME" >&2
  exit 2
fi
PROJECT_HOME="$(cd "$PROJECT_HOME" && pwd)"

# Derive alias/title from the home basename when not supplied. kebab-case
# for alias (lowercase + non-alphanum → '-'), title-case via first-letter
# uppercase per word. Pure shell.
PROJECT_BASENAME="$(basename "$PROJECT_HOME")"
if [[ -z "$PROJECT_ALIAS" ]]; then
  PROJECT_ALIAS="$(printf '%s' "$PROJECT_BASENAME" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -e 's/[^a-z0-9]/-/g' -e 's/--*/-/g' -e 's/^-//' -e 's/-$//')"
  if [[ -z "$PROJECT_ALIAS" ]]; then
    echo "error: could not derive alias from '$PROJECT_BASENAME'; pass --alias explicitly." >&2
    exit 2
  fi
  # Ensure leading character is a letter per § 11.1
  if [[ ! "$PROJECT_ALIAS" =~ ^[a-z] ]]; then
    PROJECT_ALIAS="p-${PROJECT_ALIAS}"
  fi
fi
if [[ -z "$PROJECT_TITLE" ]]; then
  # Title-case: replace separators with space, uppercase first letter of each word
  PROJECT_TITLE="$(printf '%s' "$PROJECT_BASENAME" \
    | sed -e 's/[-_]/ /g' \
    | awk '{for(i=1;i<=NF;i++){$i=toupper(substr($i,1,1)) tolower(substr($i,2))}; print}')"
fi

# Slug sanity check
if [[ ! "$PROJECT_ALIAS" =~ ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ ]]; then
  echo "error: --alias '$PROJECT_ALIAS' is not a valid slug (CONVENTIONS § 11.1)." >&2
  exit 2
fi

BRAIN_PATH="${PROJECT_HOME}/project-brain"

# ---------------------------------------------------------------------------
# 3. Locate the pack's asset dir
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ASSETS="${PACK_ROOT}/assets"

if [[ ! -d "$ASSETS" ]]; then
  echo "error: pack asset directory not found at ${ASSETS}" >&2
  exit 2
fi

for required in \
  "${PACK_ROOT}/CONVENTIONS.md" \
  "${ASSETS}/NODE-template.md" \
  "${ASSETS}/thread-index-template.md" \
  "${ASSETS}/current-state-template.md"; do
  if [[ ! -f "$required" ]]; then
    echo "error: required pack asset missing: $required" >&2
    exit 2
  fi
done

# ---------------------------------------------------------------------------
# 4. Existing-brain handling
# ---------------------------------------------------------------------------

if [[ -d "$BRAIN_PATH" && -f "${BRAIN_PATH}/CONVENTIONS.md" ]]; then
  if [[ "$FORCE" -eq 1 ]]; then
    TS="$(date -u +%Y%m%d-%H%M%S)"
    mv "$BRAIN_PATH" "${BRAIN_PATH}.bak.${TS}"
  else
    echo "error: project-brain already scaffolded at ${BRAIN_PATH}." >&2
    echo "       Pass --force to back up the existing dir to project-brain.bak.<ts>/ and scaffold fresh." >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# 5. Scaffold the skeleton
# ---------------------------------------------------------------------------

mkdir -p "${BRAIN_PATH}/tree" "${BRAIN_PATH}/threads" "${BRAIN_PATH}/archive"
touch \
  "${BRAIN_PATH}/threads/.gitkeep" \
  "${BRAIN_PATH}/archive/.gitkeep" \
  "${BRAIN_PATH}/tree/.gitkeep"

# rc4+: the tree starts EMPTY. No tree/NODE.md and no default domain
# subdir. The first successful promote-thread-to-tree creates the
# relevant tree/<domain>/NODE.md on demand. This matches the user's
# mental model — ideas live in threads/ flat, and only *decisions* that
# survive promotion reach the tree. Scaffolding an unused directory
# hierarchy at install was a reference-implementation artifact, not
# something the pipeline requires.

# Optional explicit initial domain — only when users pass --domain
# explicitly. Rare; default is to skip.
if [[ -n "$DOMAIN" ]]; then
  if [[ ! "$DOMAIN" =~ ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ ]]; then
    echo "error: --domain '$DOMAIN' is not a valid slug." >&2
    exit 2
  fi
  mkdir -p "${BRAIN_PATH}/tree/${DOMAIN}"
  cp "${ASSETS}/NODE-template.md" "${BRAIN_PATH}/tree/${DOMAIN}/NODE.md"
  NODE_ID="node-${PROJECT_ALIAS}-${DOMAIN}"
  NODE_TITLE="${DOMAIN}"
  CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sed -i.bak \
    -e "s|{{NODE_ID}}|${NODE_ID}|g" \
    -e "s|{{NODE_TITLE}}|${NODE_TITLE}|g" \
    -e "s|{{CREATED_AT}}|${CREATED_AT}|g" \
    -e "s|{{OWNER}}|${OWNER}|g" \
    -e "s|{{PRIMARY_PROJECT}}|${PROJECT_ALIAS}|g" \
    -e "s|{{NODE_DOMAIN}}|${DOMAIN}|g" \
    "${BRAIN_PATH}/tree/${DOMAIN}/NODE.md"
  rm "${BRAIN_PATH}/tree/${DOMAIN}/NODE.md.bak"
fi

# thread-index.md and current-state.md
for tpl in thread-index current-state; do
  cp "${ASSETS}/${tpl}-template.md" "${BRAIN_PATH}/${tpl}.md"
  sed -i.bak \
    -e "s|{{PRIMARY_PROJECT}}|${PROJECT_ALIAS}|g" \
    -e "s|{{PROJECT_TITLE}}|${PROJECT_TITLE}|g" \
    "${BRAIN_PATH}/${tpl}.md"
  rm "${BRAIN_PATH}/${tpl}.md.bak"
done

# CONVENTIONS.md — copy the pack's canonical copy verbatim. § 10
# placeholders can be filled in interactively later via --interactive;
# fresh installs start with the template text.
cp "${PACK_ROOT}/CONVENTIONS.md" "${BRAIN_PATH}/CONVENTIONS.md"

# If we're using the TODO@example.com owner placeholder, prepend a
# visible HTML-comment TODO marker to § 10 so the user sees it on first
# open. Find the "## 10." line and insert the marker right above it.
if [[ "$OWNER_SOURCE" == "placeholder" ]]; then
  python3 - "$BRAIN_PATH/CONVENTIONS.md" <<'PY' 2>/dev/null || true
import sys, pathlib
p = pathlib.Path(sys.argv[1])
text = p.read_text()
marker = (
  "<!-- TODO(project-brain init): The brain was scaffolded with owner = \"TODO@example.com\"\n"
  "     because no --owner <email> was supplied. When you're ready (typically before\n"
  "     your first commit, or at the latest before running promote-thread-to-tree),\n"
  "     replace every `owner: TODO@example.com` reference in this brain:\n"
  "       CONVENTIONS.md (this file)\n"
  "       any thread.md you've created\n"
  "       ~/.config/project-brain/projects.yaml (if a registry entry was written)\n"
  "     Then delete this TODO block. -->\n\n"
)
# Insert before "## 10."
lines = text.splitlines(keepends=True)
out = []
inserted = False
for line in lines:
    if not inserted and line.startswith("## 10."):
        out.append(marker)
        inserted = True
    out.append(line)
p.write_text("".join(out))
PY
fi

# Per-project config.yaml
cat > "${BRAIN_PATH}/config.yaml" <<YAML
# Per-project project-brain configuration. Optional. See CONVENTIONS § 2.1.
primary_project: ${PROJECT_ALIAS}

# Cross-project aliases this brain references (empty by default).
aliases: {}

# Operational knobs. Defaults shown.
verbosity: terse
transcript_logging: on
YAML

# .gitignore — default to ignoring per-thread transcripts + attachments.
cat > "${BRAIN_PATH}/.gitignore" <<'GITIGNORE'
# project-brain v1.0.0-rc4 defaults — transcripts + attachments.
# Delete these lines if you want to commit them to git.
threads/*/transcript.md
threads/*/attachments/
archive/*/transcript.md
archive/*/attachments/
GITIGNORE

# ---------------------------------------------------------------------------
# 6. Optional: user-global registry entry
# ---------------------------------------------------------------------------

if [[ "$WITH_REGISTRY" -eq 1 ]]; then
  REG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/project-brain"
  REG_PATH="${REG_DIR}/projects.yaml"
  mkdir -p "$REG_DIR"
  if [[ ! -f "$REG_PATH" ]]; then
    cat > "$REG_PATH" <<'REG'
# User-global project-brain registry. Optional. See CONVENTIONS § 2.2.
# Top-level keys are aliases used in cross-project soft_links.

REG
  fi
  if grep -qE "^${PROJECT_ALIAS}:" "$REG_PATH" 2>/dev/null; then
    echo "warn: registry entry for '${PROJECT_ALIAS}' already present in ${REG_PATH}; not modifying." >&2
  else
    cat >> "$REG_PATH" <<YAML
${PROJECT_ALIAS}:
  root: ${PROJECT_HOME}
  brain: ${BRAIN_PATH}
YAML
  fi
fi

# ---------------------------------------------------------------------------
# 7. Optional: git init + bootstrap commit
# ---------------------------------------------------------------------------

if [[ "$INIT_GIT" -eq 1 ]]; then
  cd "$PROJECT_HOME"
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git init --quiet
  fi
  git add project-brain/ >/dev/null 2>&1 || true
  # Commit only if there's something staged (the add may no-op if already committed).
  if ! git diff --cached --quiet 2>/dev/null; then
    git commit --quiet -m "chore(brain): scaffold project-brain for ${PROJECT_ALIAS}"
  fi
fi

# ---------------------------------------------------------------------------
# 8. Terse success report — one line, stdout.
# ---------------------------------------------------------------------------

echo "Initialized project-brain in ${BRAIN_PATH} (alias: ${PROJECT_ALIAS}, owner: ${OWNER})."
if [[ -n "$HOME_SOURCE" ]]; then
  echo "  project home auto-detected via ${HOME_SOURCE}."
fi
if [[ "$OWNER_SOURCE" == "placeholder" ]]; then
  echo "  owner = TODO@example.com placeholder; replace in CONVENTIONS § 10 when ready."
fi
# No git-commit reminder at init time by design: capture/refine/debate are
# all git-free per rc4. Mentioning git here cues a workflow model the pack
# has intentionally moved away from. Git enters at promote-thread-to-tree,
# where it has to — not before.

exit 0
