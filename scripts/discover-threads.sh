#!/usr/bin/env bash
# discover-threads.sh — one-shot thread query.
#
# Walks threads/*/thread.md and optionally archive/*/thread.md, parses each
# file's YAML frontmatter, applies filters, sorts, and renders the matching
# rows. Pure read-only; replaces the previous LLM-orchestrated multi-step
# walk that closed bug #2 (P2: discover-threads slow).
#
# Usage:
#   scripts/discover-threads.sh \
#       --brain=<path>                   \
#       [--status=<csv>]                 \  # active,parked,in-review,archived (default: all non-archived)
#       [--owner=<substring>]            \
#       [--assigned=<substring>]         \
#       [--maturity=<csv>]               \  # exploring,refining,locking
#       [--domain=<prefix>]              \  # prefix match on tree_domain
#       [--modified-before=<ISO8601>]    \
#       [--modified-after=<ISO8601>]     \
#       [--review-requirement=<value>]   \
#       [--has-pr | --no-pr]             \
#       [--unpark-trigger-set]           \
#       [--include-archived]             \
#       [--sort=<key>]                   \  # modified-desc | created-desc | status | slug
#       [--limit=<N>]                    \
#       [--format=<fmt>]                    # table (default) | json | csv | yaml | paths
#
# Exit codes:
#   0   matched rows printed (zero rows is still success)
#   2   invocation error (bad flag, brain not found)

set -euo pipefail

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------

BRAIN=""
STATUS_FILTER=""
OWNER_FILTER=""
ASSIGNED_FILTER=""
MATURITY_FILTER=""
DOMAIN_PREFIX=""
MODIFIED_BEFORE=""
MODIFIED_AFTER=""
REVIEW_REQ=""
HAS_PR=""
NO_PR=""
UNPARK_TRIGGER=""
INCLUDE_ARCHIVED=0
SORT="modified-desc"
LIMIT=""
FORMAT="table"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain=*)               BRAIN="${1#*=}"; shift ;;
    --brain)                 BRAIN="$2"; shift 2 ;;
    --status=*)              STATUS_FILTER="${1#*=}"; shift ;;
    --status)                STATUS_FILTER="$2"; shift 2 ;;
    --owner=*)               OWNER_FILTER="${1#*=}"; shift ;;
    --owner)                 OWNER_FILTER="$2"; shift 2 ;;
    --assigned=*)            ASSIGNED_FILTER="${1#*=}"; shift ;;
    --assigned)              ASSIGNED_FILTER="$2"; shift 2 ;;
    --maturity=*)            MATURITY_FILTER="${1#*=}"; shift ;;
    --maturity)              MATURITY_FILTER="$2"; shift 2 ;;
    --domain=*)              DOMAIN_PREFIX="${1#*=}"; shift ;;
    --domain)                DOMAIN_PREFIX="$2"; shift 2 ;;
    --modified-before=*)     MODIFIED_BEFORE="${1#*=}"; shift ;;
    --modified-before)       MODIFIED_BEFORE="$2"; shift 2 ;;
    --modified-after=*)      MODIFIED_AFTER="${1#*=}"; shift ;;
    --modified-after)        MODIFIED_AFTER="$2"; shift 2 ;;
    --review-requirement=*)  REVIEW_REQ="${1#*=}"; shift ;;
    --review-requirement)    REVIEW_REQ="$2"; shift 2 ;;
    --has-pr)                HAS_PR=1; shift ;;
    --no-pr)                 NO_PR=1; shift ;;
    --unpark-trigger-set)    UNPARK_TRIGGER=1; shift ;;
    --include-archived)      INCLUDE_ARCHIVED=1; shift ;;
    --sort=*)                SORT="${1#*=}"; shift ;;
    --sort)                  SORT="$2"; shift 2 ;;
    --limit=*)               LIMIT="${1#*=}"; shift ;;
    --limit)                 LIMIT="$2"; shift 2 ;;
    --format=*)              FORMAT="${1#*=}"; shift ;;
    --format)                FORMAT="$2"; shift 2 ;;
    -h|--help)               head -n 35 "$0"; exit 0 ;;
    *)                       echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$BRAIN" ]]; then
  echo "error: --brain is required." >&2
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

case "$SORT" in
  modified-desc|created-desc|status|slug) ;;
  *) echo "error: --sort must be modified-desc | created-desc | status | slug (got '$SORT')." >&2; exit 2 ;;
esac
case "$FORMAT" in
  table|json|csv|yaml|paths) ;;
  *) echo "error: --format must be table | json | csv | yaml | paths (got '$FORMAT')." >&2; exit 2 ;;
esac
if [[ -n "$LIMIT" && ! "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "error: --limit must be a non-negative integer (got '$LIMIT')." >&2
  exit 2
fi
if [[ -n "$HAS_PR" && -n "$NO_PR" ]]; then
  echo "error: --has-pr and --no-pr are mutually exclusive." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Walk + parse + filter + sort + render via Python — keeps this readable
# instead of becoming an awk soup. Pure stdlib (with the _yaml_mini fallback
# the pack already ships); no PyYAML hard dep.
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

python3 - <<PY
import os, sys, re, json, glob

# Use the pack's own yaml import strategy: PyYAML if available, _yaml_mini fallback.
try:
    import yaml
except ImportError:
    sys.path.insert(0, os.path.join("${SCRIPT_DIR}", "verify_tree"))
    import _yaml_mini as yaml  # type: ignore

brain                = "$BRAIN"
status_filter        = "$STATUS_FILTER"
owner_filter         = "$OWNER_FILTER"
assigned_filter      = "$ASSIGNED_FILTER"
maturity_filter      = "$MATURITY_FILTER"
domain_prefix        = "$DOMAIN_PREFIX"
modified_before      = "$MODIFIED_BEFORE"
modified_after       = "$MODIFIED_AFTER"
review_req           = "$REVIEW_REQ"
has_pr               = "$HAS_PR"
no_pr                = "$NO_PR"
unpark_trigger       = "$UNPARK_TRIGGER"
include_archived     = "$INCLUDE_ARCHIVED" == "1"
sort_key             = "$SORT"
limit_str            = "$LIMIT"
fmt                  = "$FORMAT"

def parse_csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else []

# ---- Walk + parse ------------------------------------------------------------

rows = []
locations = ["threads"]
if include_archived or "archived" in parse_csv(status_filter):
    locations.append("archive")

for loc in locations:
    loc_dir = os.path.join(brain, loc)
    if not os.path.isdir(loc_dir):
        continue
    for slug_dir in sorted(glob.glob(os.path.join(loc_dir, "*", ""))):
        thread_md = os.path.join(slug_dir, "thread.md")
        if not os.path.isfile(thread_md):
            continue
        slug = os.path.basename(os.path.dirname(slug_dir))
        if slug.startswith("."):
            continue
        text = open(thread_md, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue
        rows.append({
            "loc":                 loc,
            "slug":                slug,
            "id":                  fm.get("id", slug),
            "title":               fm.get("title", slug),
            "status":              fm.get("status", "unknown"),
            "maturity":            fm.get("maturity"),
            "owner":               fm.get("owner", ""),
            "primary_project":     fm.get("primary_project", ""),
            "tree_domain":         fm.get("tree_domain") or "",
            "assigned_to":         fm.get("assigned_to") or [],
            "review_requirement":  fm.get("review_requirement") or "",
            "tree_prs":            fm.get("tree_prs") or [],
            "promoted_to":         fm.get("promoted_to") or [],
            "promoted_at":         fm.get("promoted_at") or [],
            "parked_at":           fm.get("parked_at"),
            "parked_by":           fm.get("parked_by"),
            "unpark_trigger":      fm.get("unpark_trigger") or "",
            "created_at":          str(fm.get("created_at") or ""),
            "last_modified_at":    str(fm.get("last_modified_at") or fm.get("created_at") or ""),
            "path":                os.path.relpath(thread_md, brain),
        })

# ---- Filter ------------------------------------------------------------------

statuses = set(parse_csv(status_filter))
if not statuses:
    # Default: exclude archived unless explicitly --include-archived or --status=archived
    statuses = {"active", "parked", "in-review"}
    if include_archived:
        statuses.add("archived")
maturities = set(parse_csv(maturity_filter))

def keep(r):
    if r["status"] not in statuses:
        return False
    if maturities and (r["maturity"] not in maturities):
        return False
    if owner_filter and owner_filter.lower() not in (r["owner"] or "").lower():
        return False
    if assigned_filter:
        haystack = " ".join(str(x) for x in (r["assigned_to"] if isinstance(r["assigned_to"], list) else [r["assigned_to"]]))
        if assigned_filter.lower() not in haystack.lower():
            return False
    if domain_prefix and not (r["tree_domain"] or "").startswith(domain_prefix):
        return False
    if modified_before and r["last_modified_at"] and r["last_modified_at"] > modified_before:
        return False
    if modified_after and r["last_modified_at"] and r["last_modified_at"] < modified_after:
        return False
    if review_req and r["review_requirement"] != review_req:
        return False
    if has_pr == "1" and not r["tree_prs"]:
        return False
    if no_pr == "1" and r["tree_prs"]:
        return False
    if unpark_trigger == "1":
        if r["status"] != "parked" or not r["unpark_trigger"]:
            return False
    return True

rows = [r for r in rows if keep(r)]

# ---- Sort --------------------------------------------------------------------

if sort_key == "modified-desc":
    rows.sort(key=lambda r: (r["last_modified_at"], r["slug"]), reverse=True)
elif sort_key == "created-desc":
    rows.sort(key=lambda r: (r["created_at"], r["slug"]), reverse=True)
elif sort_key == "status":
    rows.sort(key=lambda r: (r["status"], r["slug"]))
elif sort_key == "slug":
    rows.sort(key=lambda r: r["slug"])

if limit_str:
    rows = rows[: int(limit_str)]

# ---- Render ------------------------------------------------------------------

def short_ts(ts):
    return (ts or "")[:19]

def to_table(rs):
    # Markdown table — renders cleanly in Cowork chat / Cursor / GitHub /
    # any chat surface that handles markdown. The slug cell is wrapped in
    # a clickable file:// link to the thread.md so the user can drill in
    # one click. (Earlier ASCII-table renderer didn't expose a path at
    # all — users had to guess where the thread lived.)
    if not rs:
        return "_(no threads matched)_"
    hdr = ["slug", "status", "maturity", "owner", "assigned", "modified", "domain", "PR"]
    out = []
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "|".join(["---"] * len(hdr)) + "|")
    for r in rs:
        assigned = ",".join(r["assigned_to"]) if isinstance(r["assigned_to"], list) else (r["assigned_to"] or "")
        pr = "OPEN" if r["tree_prs"] else ""
        # Absolute path to thread.md so file:// resolves outside the brain root.
        # Backticks escaped (\`) — this heredoc is unquoted (so $BRAIN etc.
        # expand), and bare backticks would be treated as bash command
        # substitution. The escape preserves a literal backtick in the f-string.
        abs_path = os.path.join(brain, r["path"])
        slug_cell = f"[\`{r['slug']}\`](file://{abs_path})"
        row = [
            slug_cell,
            r["status"],
            r["maturity"] or "—",
            r["owner"] or "—",
            assigned or "—",
            short_ts(r["last_modified_at"]) or "—",
            r["tree_domain"] or "—",
            pr or "—",
        ]
        # Pipe characters in any cell would break the row — escape defensively.
        row = [str(c).replace("|", "\\|") for c in row]
        out.append("| " + " | ".join(row) + " |")
    out.append("")
    out.append(f"_{len(rs)} thread{'s' if len(rs) != 1 else ''} matched_")
    return "\n".join(out)

def to_json(rs):
    return json.dumps(rs, indent=2, ensure_ascii=False, default=str)

def to_csv(rs):
    import csv as csvmod, io
    buf = io.StringIO()
    fields = ["slug","status","maturity","owner","assigned_to","last_modified_at","created_at","tree_domain","tree_prs","title","loc"]
    w = csvmod.writer(buf)
    w.writerow(fields)
    for r in rs:
        a = ";".join(r["assigned_to"]) if isinstance(r["assigned_to"], list) else str(r["assigned_to"] or "")
        prs = ";".join(str(x) for x in r["tree_prs"])
        w.writerow([r["slug"], r["status"], r["maturity"] or "", r["owner"], a,
                    r["last_modified_at"], r["created_at"], r["tree_domain"], prs, r["title"], r["loc"]])
    return buf.getvalue().rstrip()

def to_yaml(rs):
    return yaml.safe_dump(rs, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip()

def to_paths(rs):
    return "\n".join(r["path"] for r in rs)

renderers = {"table": to_table, "json": to_json, "csv": to_csv, "yaml": to_yaml, "paths": to_paths}
print(renderers[fmt](rows))
PY

exit 0
