"""Tests for verify-tree.py — stdlib-only (no pytest required).

Run with:   python3 scripts/test_verify_tree.py
Or:         python3 -m unittest scripts/test_verify_tree.py

Each test builds a minimal in-memory brain under a tmp dir, runs the
validator's main() with --format=json, and asserts on the result.
Covers every V-NN / N-NN code with at least one pass case and one fail case
where meaningful, plus --rebuild-index happy path + dry-run diff.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "verify-tree.py"

# Import the verify_tree package directly. The hyphenated `verify-tree.py`
# shim lives at the same path and is still what CI invokes, but tests can
# skip the shim and pull the package straight in.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verify_tree as vt  # noqa: E402


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def run_validator(
    brain: Path,
    *extra_args: str,
    as_json: bool = True,
) -> tuple[int, dict, str, str]:
    """Run main() in-process. Return (exit_code, parsed_json, stdout, stderr)."""
    args = ["--brain", str(brain)]
    if as_json and "--rebuild-index" not in extra_args:
        args += ["--format", "json"]
    args += list(extra_args)
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        exit_code = vt.main(args)
    out = out_buf.getvalue()
    err = err_buf.getvalue()
    data: dict = {}
    if as_json and out.strip() and "--rebuild-index" not in extra_args:
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            pass
    return exit_code, data, out, err


def write(p: Path, text: str) -> None:
    """Write a templated fixture file.

    The templates in this file use 8-space indentation inside docstrings for
    readability. This function strips that indent from every line (lines with
    less indent keep what they have). That way multi-line `extras` arguments
    passed in at zero indent don't throw off `textwrap.dedent`.
    """
    p.parent.mkdir(parents=True, exist_ok=True)
    if text.startswith("\n"):
        text = text[1:]
    # Find first non-empty line's indent; use that as the template indent.
    indent = 0
    for line in text.split("\n"):
        if line.strip():
            indent = len(line) - len(line.lstrip(" "))
            break
    if indent:
        prefix = " " * indent
        new_lines = []
        for line in text.split("\n"):
            if line.startswith(prefix):
                new_lines.append(line[indent:])
            else:
                new_lines.append(line.lstrip(" ") if not line.strip() else line)
        text = "\n".join(new_lines)
    p.write_text(text, encoding="utf-8")


def make_brain(tmp_path: Path) -> Path:
    # Per CONVENTIONS § 1 the brain root IS the thoughts/ directory — it
    # contains CONVENTIONS.md directly plus threads/, tree/, archive/ children.
    # (Pre-F6 this helper nested everything under a redundant `thoughts/` dir;
    # the F5/F6 fix restored the canonical single-layer layout.)
    brain = tmp_path / "brain"
    brain.mkdir()
    write(
        brain / "CONVENTIONS.md",
        """
        ---
        id: conv
        title: Conventions
        primary_project: demo
        kind: conventions
        project_title: Demo
        ---

        # Conventions

        body.
        """,
    )
    (brain / "threads").mkdir()
    (brain / "tree").mkdir()
    (brain / "archive").mkdir()
    return brain


def make_thread(
    brain: Path,
    slug: str,
    status: str = "active",
    maturity: Optional[str] = "exploring",
    extras: str = "",
    location: str = "threads",
    title: str = "A Thread",
) -> Path:
    mat_line = f"maturity: {maturity}" if maturity is not None else ""
    p = brain / location / slug / "thread.md"
    write(
        p,
        f"""
        ---
        id: {slug}
        title: {title}
        created_at: 2026-04-01T00:00:00Z
        owner: alice
        primary_project: demo
        status: {status}
        {mat_line}
        soft_links: []
        promoted_to: []
        promoted_at: []
        tree_prs: []
        last_modified_at: 2026-04-02T00:00:00Z
        {extras}
        ---

        # {title}

        body.
        """,
    )
    return p


def make_leaf(
    brain: Path,
    domain: str,
    slug: str,
    status: str = "decided",
    extras: str = "",
    staging_thread: Optional[str] = None,
    title: Optional[str] = None,
) -> Path:
    t = title or f"Leaf {slug}"
    if staging_thread:
        parent = brain / "threads" / staging_thread / "tree-staging" / domain
    else:
        parent = brain / "tree" / domain
    p = parent / f"{slug}.md"
    write(
        p,
        f"""
        ---
        id: {slug}
        title: {t}
        created_at: 2026-04-01T00:00:00Z
        owner: alice
        primary_project: demo
        status: {status}
        node_type: leaf
        domain: {domain}
        soft_links: []
        {extras}
        ---

        # {t}

        body.
        """,
    )
    return p


def make_node(brain: Path, domain: str, leaves: Optional[list] = None) -> Path:
    leaves = leaves or []
    parent = brain / "tree" / domain
    p = parent / "NODE.md"
    leaves_md = "\n".join(f"- [l]({l})" for l in leaves) or "<!-- none -->"
    write(
        p,
        f"""
        ---
        id: node-{domain.replace('/', '-')}
        title: {domain} node
        created_at: 2026-04-01T00:00:00Z
        owner: alice
        primary_project: demo
        status: decided
        node_type: node
        domain: {domain}
        soft_links: []
        children: []
        ---

        # {domain} node

        ## Leaves

        {leaves_md}

        ## Sub-nodes
        """,
    )
    return p


class BaseTest(unittest.TestCase):
    """Base class that provides a tmp_path attribute per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class SmokeTests(BaseTest):
    def test_help_works(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("verify-tree", result.stdout)

    def test_empty_brain_is_clean(self):
        brain = make_brain(self.tmp_path)
        exit_code, data, _, _ = run_validator(brain)
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["summary"]["errors"], 0)

    def test_valid_thread_passes(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        exit_code, data, _, _ = run_validator(brain)
        codes = [v["code"] for v in data["errors"]]
        self.assertEqual(codes, [])
        self.assertEqual(exit_code, 0)


# ---------------------------------------------------------------------------
# V-01..V-21, N-01..N-04
# ---------------------------------------------------------------------------


class InvariantTests(BaseTest):
    def _run(self, brain: Path, *args: str):
        return run_validator(brain, *args)

    # V-01
    def test_v01_title_mismatch(self):
        brain = make_brain(self.tmp_path)
        p = make_thread(brain, "alpha")
        text = p.read_text().replace("# A Thread", "# Different Heading")
        p.write_text(text)
        code, data, *_ = run_validator(brain)
        self.assertIn("V-01", [v["code"] for v in data["errors"]])
        self.assertEqual(code, 1)

    # V-02
    def test_v02_domain_matches(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(brain, "data", "widget")
        _, data, *_ = self._run(brain)
        self.assertNotIn("V-02", [v["code"] for v in data["errors"]])

    def test_v02_domain_mismatch(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(brain, "data", "widget")
        p = brain / "tree" / "data" / "widget.md"
        p.write_text(p.read_text().replace("domain: data", "domain: other"))
        _, data, *_ = self._run(brain)
        self.assertIn("V-02", [v["code"] for v in data["errors"]])

    # V-03
    def test_v03_dangling_soft_link(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "/tree/nope/missing.md"\n    rel: x\n',
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-03", [v["code"] for v in data["errors"]])

    def test_v03_external_url_ok(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "https://example.com"\n    rel: x\n',
        )
        code, data, *_ = run_validator(brain)
        self.assertNotIn("V-03", [v["code"] for v in data["errors"]])
        self.assertEqual(code, 0)

    # V-04
    def test_v04_unlisted_leaf(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", [])
        make_leaf(brain, "data", "orphan")
        _, data, *_ = self._run(brain)
        self.assertIn("V-04", [v["code"] for v in data["errors"]])

    # V-05
    def test_v05_broken_leaf_link(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["ghost.md"])
        _, data, *_ = self._run(brain)
        self.assertIn("V-05", [v["code"] for v in data["errors"]])

    # V-06
    def test_v06_missing_required(self):
        brain = make_brain(self.tmp_path)
        p = make_thread(brain, "alpha")
        p.write_text(p.read_text().replace("owner: alice\n", ""))
        _, data, *_ = self._run(brain)
        self.assertIn("V-06", [v["code"] for v in data["errors"]])

    # V-07
    def test_v07_in_review_requires_locking(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha", status="in-review", maturity="exploring")
        _, data, *_ = self._run(brain)
        self.assertIn("V-07", [v["code"] for v in data["errors"]])

    def test_v07_archived_no_maturity(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "gamma", status="archived", maturity="locking", location="archive")
        _, data, *_ = self._run(brain)
        self.assertIn("V-07", [v["code"] for v in data["errors"]])

    # V-08
    def test_v08_parity_fail(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras='promoted_to:\n  - "/tree/x.md"\npromoted_at: []\n',
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-08", [v["code"] for v in data["errors"]])

    # V-09
    def test_v09_built_requires_built_in(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(brain, "data", "widget", status="built")
        _, data, *_ = self._run(brain)
        self.assertIn("V-09", [v["code"] for v in data["errors"]])

    def test_v09_decided_in_staging(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        make_leaf(brain, "data", "widget", status="decided", staging_thread="alpha")
        _, data, *_ = self._run(brain)
        self.assertIn("V-09", [v["code"] for v in data["errors"]])

    # V-10
    def test_v10_node_must_be_decided(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data")
        p = brain / "tree" / "data" / "NODE.md"
        p.write_text(p.read_text().replace("status: decided", "status: draft"))
        _, data, *_ = self._run(brain)
        self.assertIn("V-10", [v["code"] for v in data["errors"]])

    # V-11
    def test_v11_invalid_pair(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        spec_path = brain / "tree" / "data" / "widget-impl.md"
        write(
            spec_path,
            """
            ---
            id: widget-impl
            title: Widget — Implementation Spec
            created_at: 2026-04-01T00:00:00Z
            owner: alice
            primary_project: demo
            kind: impl-spec
            source_leaf: tree/data/widget.md
            status: draft
            soft_links: []
            ---

            # Widget — Implementation Spec

            body.
            """,
        )
        make_thread(brain, "alpha")
        make_leaf(
            brain,
            "data",
            "widget",
            status="building",
            extras="impl_spec: widget-impl\nimpl_thread: alpha\n",
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-11", [v["code"] for v in data["errors"]])

    # V-12
    def test_v12_parked_requires_fields(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha", status="parked", maturity="refining")
        _, data, *_ = self._run(brain)
        self.assertIn("V-12", [v["code"] for v in data["errors"]])

    def test_v12_active_rejects_park_fields(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras='parked_at: 2026-04-01T00:00:00Z\nparked_by: alice\nparked_reason: "later"\n',
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-12", [v["code"] for v in data["errors"]])

    def test_v12_parked_with_fields_ok(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            status="parked",
            maturity="refining",
            extras='parked_at: 2026-04-01T00:00:00Z\nparked_by: alice\nparked_reason: "later"\n',
        )
        _, data, *_ = self._run(brain)
        self.assertNotIn("V-12", [v["code"] for v in data["errors"]])

    # V-13
    def test_v13_hardening_requires_pre_status(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(brain, "data", "widget", status="hardening")
        _, data, *_ = self._run(brain)
        self.assertIn("V-13", [v["code"] for v in data["errors"]])

    def test_v13_non_hardening_rejects_pre_status(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(
            brain,
            "data",
            "widget",
            status="decided",
            extras="pre_hardening_status: decided\n",
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-13", [v["code"] for v in data["errors"]])

    # V-14
    def test_v14_dangling_source_thread(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(
            brain,
            "data",
            "widget",
            extras="source_thread: ghost-thread\n",
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-14", [v["code"] for v in data["errors"]])

    def test_v14_resolved_source_thread_ok(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        make_node(brain, "data", ["widget.md"])
        make_leaf(brain, "data", "widget", extras="source_thread: alpha\n")
        _, data, *_ = self._run(brain)
        self.assertNotIn("V-14", [v["code"] for v in data["errors"]])

    # V-15
    def test_v15_cycle_detected(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "/threads/beta/thread.md"\n    rel: x\n',
        )
        make_thread(
            brain,
            "beta",
            extras='soft_links:\n  - uri: "/threads/alpha/thread.md"\n    rel: x\n',
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-15", [v["code"] for v in data["errors"]])

    # V-16
    def test_v16_self_reference(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "/threads/alpha/thread.md"\n    rel: x\n',
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-16", [v["code"] for v in data["errors"]])

    # V-17
    def test_v17_duplicate_promoted_to(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras=(
                'promoted_to:\n'
                '  - "/tree/x.md"\n'
                '  - "/tree/x.md"\n'
                'promoted_at:\n'
                '  - 2026-04-01T00:00:00Z\n'
                '  - 2026-04-02T00:00:00Z\n'
            ),
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-17", [v["code"] for v in data["errors"]])

    # V-18
    def test_v18_non_monotonic(self):
        brain = make_brain(self.tmp_path)
        make_thread(
            brain,
            "alpha",
            extras=(
                'promoted_to:\n'
                '  - "/tree/x.md"\n'
                '  - "/tree/y.md"\n'
                'promoted_at:\n'
                '  - 2026-04-10T00:00:00Z\n'
                '  - 2026-04-01T00:00:00Z\n'
            ),
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-18", [v["code"] for v in data["errors"]])

    # V-19 / N-04
    def test_v19_debate_gap(self):
        brain = make_brain(self.tmp_path)
        t_dir = brain / "threads" / "alpha"
        make_thread(brain, "alpha")
        (t_dir / "debate" / "round-01").mkdir(parents=True)
        (t_dir / "debate" / "round-03").mkdir(parents=True)
        _, data, *_ = self._run(brain)
        codes = [v["code"] for v in data["errors"]]
        self.assertTrue("V-19" in codes or "N-04" in codes)

    def test_v19_sequential_ok(self):
        brain = make_brain(self.tmp_path)
        t_dir = brain / "threads" / "alpha"
        make_thread(brain, "alpha")
        (t_dir / "debate" / "round-01").mkdir(parents=True)
        (t_dir / "debate" / "round-02").mkdir(parents=True)
        _, data, *_ = self._run(brain)
        self.assertNotIn("V-19", [v["code"] for v in data["errors"]])

    # V-20
    def test_v20_dangling_source_debate(self):
        brain = make_brain(self.tmp_path)
        make_node(brain, "data", ["widget.md"])
        make_leaf(
            brain,
            "data",
            "widget",
            extras="source_debate: threads/ghost/debate/round-01\n",
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-20", [v["code"] for v in data["errors"]])

    # V-21
    def test_v21_non_ascii_filename(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        bad = brain / "threads" / "alpha" / "bad name.md"
        write(
            bad,
            """
            ---
            id: badname
            title: Bad Name
            created_at: 2026-04-01T00:00:00Z
            owner: alice
            primary_project: demo
            status: draft
            node_type: leaf
            domain: ignored
            soft_links: []
            ---

            # Bad Name
            """,
        )
        _, data, *_ = self._run(brain)
        self.assertIn("V-21", [v["code"] for v in data["errors"]])

    # N-01 warning
    def test_n01_bad_id_is_warning(self):
        brain = make_brain(self.tmp_path)
        p = make_thread(brain, "alpha")
        p.write_text(p.read_text().replace("id: alpha", "id: Bad_ID"))
        code, data, *_ = run_validator(brain)
        self.assertIn("N-01", [v["code"] for v in data["warnings"]])
        self.assertEqual(code, 0)

    def test_n01_warnings_as_errors(self):
        brain = make_brain(self.tmp_path)
        p = make_thread(brain, "alpha")
        p.write_text(p.read_text().replace("id: alpha", "id: Bad_ID"))
        code, _, *_ = self._run(brain, "--warnings-as-errors")
        self.assertEqual(code, 1)

    # N-02
    def test_n02_wrong_casing(self):
        # Case-insensitive filesystems (macOS default HFS+/APFS, Windows NTFS)
        # cannot host both ``thread.md`` and ``Thread.md`` in the same
        # directory: writing the wrong-cased name silently clobbers the
        # lowercase file (its disk name stays lowercase), so the fixture
        # never produces the scenario N-02 detects. Skip on those; CI
        # (ubuntu / ext4) is where the regression would land anyway.
        probe = self.tmp_path / "n02_casecheck"
        probe.mkdir()
        (probe / "file.md").write_text("a")
        try:
            (probe / "File.md").write_text("b")
            # If both files coexist on disk, FS is case-sensitive.
            names = sorted(p.name for p in probe.iterdir())
            if names != ["File.md", "file.md"]:
                self.skipTest(
                    "filesystem is case-insensitive; N-02 fixture requires "
                    "case-sensitive FS (e.g. ext4 in CI)."
                )
        except (FileExistsError, OSError):
            self.skipTest(
                "filesystem is case-insensitive; N-02 fixture requires "
                "case-sensitive FS (e.g. ext4 in CI)."
            )

        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        wrong = brain / "threads" / "alpha" / "Thread.md"
        write(
            wrong,
            """
            ---
            id: dup
            title: Dup
            created_at: 2026-04-01T00:00:00Z
            owner: alice
            primary_project: demo
            status: active
            maturity: exploring
            soft_links: []
            promoted_to: []
            promoted_at: []
            tree_prs: []
            ---

            # Dup
            """,
        )
        _, data, *_ = self._run(brain)
        self.assertIn("N-02", [v["code"] for v in data["errors"]])

    # N-03
    def test_n03_wrong_dir_case(self):
        # Case-insensitive filesystems (macOS default HFS+/APFS, Windows NTFS)
        # treat ``Threads`` and ``threads`` as the same directory, so the
        # fixture's mkdir would collide with the one make_brain() already
        # created. Skip on those; N-03 is enforced in CI (ubuntu/ext4) which
        # is where the regression would land anyway.
        probe_a = self.tmp_path / "casecheck"
        probe_a.mkdir()
        try:
            (self.tmp_path / "CASECHECK").mkdir()
        except FileExistsError:
            self.skipTest(
                "filesystem is case-insensitive; N-03 fixture requires "
                "case-sensitive FS (e.g. ext4 in CI)."
            )
        brain = make_brain(self.tmp_path)
        (brain / "Threads").mkdir()
        _, data, *_ = self._run(brain)
        self.assertIn("N-03", [v["code"] for v in data["errors"]])


# ---------------------------------------------------------------------------
# --rebuild-index
# ---------------------------------------------------------------------------


class RebuildIndexTests(BaseTest):
    def test_rebuild_index_generates_files(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        make_thread(
            brain,
            "beta",
            status="parked",
            maturity="refining",
            extras='parked_at: 2026-04-05T00:00:00Z\nparked_by: alice\nparked_reason: "pause"\n',
        )
        code, _, out, err = run_validator(brain, "--rebuild-index", as_json=False)
        self.assertEqual(code, 0, err)
        idx = (brain / "thread-index.md").read_text()
        state = (brain / "current-state.md").read_text()
        self.assertIn("Thread Index", idx)
        self.assertIn("alpha", idx)
        self.assertIn("beta", idx)
        self.assertIn("Current State", state)

    def test_rebuild_index_dry_run_no_writes(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        code, _, _, err = run_validator(
            brain, "--rebuild-index", "--dry-run", as_json=False
        )
        self.assertEqual(code, 0)
        self.assertFalse((brain / "thread-index.md").exists())
        self.assertFalse((brain / "current-state.md").exists())

    def test_rebuild_index_deterministic(self):
        # Rebuild output is byte-stable on an unchanged brain — the
        # banner timestamp is now derived from source frontmatter
        # (high-water mark), not datetime.now().
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        make_thread(brain, "beta")
        run_validator(brain, "--rebuild-index", as_json=False)
        content1 = (brain / "thread-index.md").read_text()
        state1 = (brain / "current-state.md").read_text()
        run_validator(brain, "--rebuild-index", as_json=False)
        content2 = (brain / "thread-index.md").read_text()
        state2 = (brain / "current-state.md").read_text()
        self.assertEqual(content1, content2)
        self.assertEqual(state1, state2)

    def test_rebuild_index_refuses_on_bad_source(self):
        brain = make_brain(self.tmp_path)
        p = make_thread(brain, "alpha")
        p.write_text(p.read_text().replace("owner: alice\n", ""))
        code, _, _, err = run_validator(brain, "--rebuild-index", as_json=False)
        self.assertEqual(code, 1)
        self.assertIn("V-06", err)


# ---------------------------------------------------------------------------
# Invocation errors + extension loader
# ---------------------------------------------------------------------------


class InvocationTests(BaseTest):
    def test_no_brain_root(self):
        code, _, _, err = run_validator(self.tmp_path, as_json=False)
        self.assertEqual(code, 2)
        self.assertIn("CONVENTIONS.md", err)

    def test_mutually_exclusive_flags(self):
        brain = make_brain(self.tmp_path)
        code, _, _, err = run_validator(
            brain, "--rebuild-index", "--thread", "alpha", as_json=False
        )
        self.assertEqual(code, 2)

    def test_extension_hook(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        ext_dir = brain / "scripts" / "verify-tree.d"
        ext_dir.mkdir(parents=True)
        write(
            ext_dir / "example.py",
            """
            class V:
                def __init__(self, **kw):
                    self.__dict__.update(kw)
                def as_dict(self):
                    return dict(self.__dict__)

            def check(brain, artifacts, violations):
                violations.append(V(
                    code="X-TEST-01",
                    file="synthetic",
                    line=0,
                    message="synthetic check fired",
                    artifact_id=None,
                    severity="error",
                ))
            """,
        )
        code, data, *_ = run_validator(brain)
        codes = [v["code"] for v in data["errors"]]
        self.assertIn("X-TEST-01", codes)
        self.assertEqual(code, 1)


# ---------------------------------------------------------------------------
# v1.0.0-rc4 additions — transcript, attachments, two-layer config resolver
# ---------------------------------------------------------------------------


class V2AdditionsTests(BaseTest):
    """transcript.md + <thread>/attachments/* must not fire V-06 even with
    no frontmatter. Two-layer config resolver must prefer per-project
    aliases, fall back to global, warn when neither layer exists."""

    def test_transcript_md_without_frontmatter_is_clean(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        tx = brain / "threads" / "alpha" / "transcript.md"
        tx.write_text("# transcript\n\nuser: hello\n\nassistant: hi\n")
        code, data, *_ = run_validator(brain)
        self.assertEqual(code, 0, data.get("errors"))
        self.assertEqual(data["summary"]["errors"], 0)

    def test_attachments_dir_ignored_from_frontmatter_rules(self):
        brain = make_brain(self.tmp_path)
        make_thread(brain, "alpha")
        att = brain / "threads" / "alpha" / "attachments" / "scratch.md"
        att.parent.mkdir(parents=True, exist_ok=True)
        att.write_text("# scratch\n\nrandom notes, no frontmatter\n")
        code, data, *_ = run_validator(brain)
        self.assertEqual(code, 0, data.get("errors"))

    def test_v03_alias_warning_when_no_config_layer(self):
        brain = make_brain(self.tmp_path)
        # Thread with a cross-project alias link but NO config.yaml and NO
        # global registry → V-03 should fire as a WARNING, not an error.
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "otherproj:tree/x.md"\n    rel: x\n',
        )
        env = os.environ.copy()
        env["PROJECT_BRAIN_PROJECTS_YAML"] = "/tmp/does-not-exist-v2.yaml"
        env.pop("PROJECT_BRAIN_CONFIG", None)
        # Run via subprocess so the env var actually applies.
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--brain", str(brain), "--format", "json"],
            capture_output=True, text=True, env=env,
        )
        data = json.loads(result.stdout)
        codes_err = [v["code"] for v in data["errors"]]
        codes_warn = [v["code"] for v in data["warnings"]]
        self.assertNotIn("V-03", codes_err)
        self.assertIn("V-03", codes_warn)
        self.assertEqual(result.returncode, 0)

    def test_v03_alias_resolves_via_per_project_config(self):
        brain = make_brain(self.tmp_path)
        # Create a sibling "other brain" with a matching artifact.
        other_brain = self.tmp_path / "other-brain"
        other_brain.mkdir()
        (other_brain / "target.md").write_text("# target\n")
        # Per-project config.yaml lists the alias.
        cfg = brain / "config.yaml"
        cfg.write_text(
            "primary_project: demo\n"
            "aliases:\n"
            f"  otherproj:\n"
            f"    brain: {other_brain}\n"
        )
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "otherproj:target.md"\n    rel: x\n',
        )
        code, data, *_ = run_validator(brain)
        codes = [v["code"] for v in data["errors"] + data["warnings"]]
        self.assertNotIn("V-03", codes, data)
        self.assertEqual(code, 0)

    def test_v03_alias_error_when_layer_present_but_alias_missing(self):
        brain = make_brain(self.tmp_path)
        # config.yaml exists but doesn't list "otherproj".
        (brain / "config.yaml").write_text("primary_project: demo\naliases: {}\n")
        make_thread(
            brain,
            "alpha",
            extras='soft_links:\n  - uri: "otherproj:tree/x.md"\n    rel: x\n',
        )
        code, data, *_ = run_validator(brain)
        codes_err = [v["code"] for v in data["errors"]]
        self.assertIn("V-03", codes_err)
        self.assertEqual(code, 1)


class HostProjectRootTests(BaseTest):
    """detect_host_project_root() priority: PROJECT_BRAIN_HOME →
    COWORK_WORKSPACE_FOLDER → CODEX_PROJECT_ROOT → CLAUDE_PROJECT_ROOT →
    walk for .git → cwd fallback. Pure Python; no shell invocation."""

    def setUp(self) -> None:
        super().setUp()
        # Scrub env so each test starts from a clean slate.
        for var in (
            "PROJECT_BRAIN_HOME", "COWORK_WORKSPACE_FOLDER",
            "CODEX_PROJECT_ROOT", "CLAUDE_PROJECT_ROOT",
        ):
            os.environ.pop(var, None)

    def _detect(self, cwd: Path):
        # Import lazily so tests that don't need this helper aren't penalised.
        from verify_tree.config import detect_host_project_root
        return detect_host_project_root(cwd)

    def test_cwd_fallback(self):
        d = self.tmp_path / "lonely"
        d.mkdir()
        path, src = self._detect(d)
        self.assertEqual(path, d.resolve())
        self.assertEqual(src, "cwd")

    def test_git_root_walk(self):
        root = self.tmp_path / "myproj"
        (root / ".git").mkdir(parents=True)
        deep = root / "src" / "nested" / "here"
        deep.mkdir(parents=True)
        path, src = self._detect(deep)
        self.assertEqual(path, root.resolve())
        self.assertEqual(src, "git-root")

    def test_git_file_worktree(self):
        # Worktrees have a .git FILE (pointing at the real gitdir), not a dir.
        root = self.tmp_path / "wt"
        root.mkdir()
        (root / ".git").write_text("gitdir: /somewhere/else\n")
        nested = root / "a" / "b"
        nested.mkdir(parents=True)
        path, src = self._detect(nested)
        self.assertEqual(path, root.resolve())
        self.assertEqual(src, "git-root")

    def test_cowork_env_wins_over_git(self):
        # Env var should short-circuit the .git walk.
        cowork = self.tmp_path / "cowork-ws"
        cowork.mkdir()
        gitdir = self.tmp_path / "git-proj"
        (gitdir / ".git").mkdir(parents=True)
        nested = gitdir / "src"
        nested.mkdir()
        os.environ["COWORK_WORKSPACE_FOLDER"] = str(cowork)
        path, src = self._detect(nested)
        self.assertEqual(path, cowork.resolve())
        self.assertEqual(src, "cowork-workspace")

    def test_project_brain_home_overrides_everything(self):
        # Explicit override beats Cowork beats git.
        override = self.tmp_path / "override"
        override.mkdir()
        cowork = self.tmp_path / "cowork-ws"
        cowork.mkdir()
        os.environ["PROJECT_BRAIN_HOME"] = str(override)
        os.environ["COWORK_WORKSPACE_FOLDER"] = str(cowork)
        path, src = self._detect(self.tmp_path)
        self.assertEqual(path, override.resolve())
        self.assertEqual(src, "env:PROJECT_BRAIN_HOME")

    def test_codex_env(self):
        codex = self.tmp_path / "codex-proj"
        codex.mkdir()
        os.environ["CODEX_PROJECT_ROOT"] = str(codex)
        path, src = self._detect(self.tmp_path)
        self.assertEqual(path, codex.resolve())
        self.assertEqual(src, "codex-project")

    def test_claude_env(self):
        claude = self.tmp_path / "claude-proj"
        claude.mkdir()
        os.environ["CLAUDE_PROJECT_ROOT"] = str(claude)
        path, src = self._detect(self.tmp_path)
        self.assertEqual(path, claude.resolve())
        self.assertEqual(src, "claude-project")


if __name__ == "__main__":
    unittest.main(verbosity=2)
