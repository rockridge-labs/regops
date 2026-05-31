"""Tests for reporter.py — markdown output, JSON output, and helpers.

The Rich terminal output is exercised indirectly: it uses the same
_coverage() and _git_short_sha() helpers as the markdown path, so
testing the markdown branch covers the shared logic.
"""

import io
import json
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from regops.checker import Gap
from regops.loader import ComplianceData, Requirement
from regops.parser import TraceLink, parse_repo
from regops.reporter import (
    _coverage,
    _git_short_sha,
    report_json,
    report_markdown,
)
from regops.schema import default_schema


FIXTURES = Path(__file__).parent.parent / "fixtures"


# ----------------------------- helpers -----------------------------

def _sample_data() -> ComplianceData:
    return ComplianceData(
        requirements={
            "SR-1": Requirement(id="SR-1", type="software_requirement",
                                title="Annotated SR", safety_class="B"),
            "SR-2": Requirement(id="SR-2", type="software_requirement",
                                title="Unannotated SR", safety_class="B"),
        },
        schema=default_schema(),
    )


def _sample_links() -> list[TraceLink]:
    return [TraceLink(file="src/foo.py", line=10, reqs=["SR-1"])]


# ----------------------------- _git_short_sha -----------------------------

def test_git_sha_returns_short_sha_in_git_repo():
    sha = _git_short_sha(Path(__file__).parent.parent)
    assert sha is not None
    assert re.fullmatch(r"[0-9a-f]{7,40}", sha), f"unexpected SHA format: {sha!r}"


def test_git_sha_returns_none_outside_git_repo():
    with tempfile.TemporaryDirectory() as tmp:
        sha = _git_short_sha(Path(tmp))
        assert sha is None


# ----------------------------- _coverage -----------------------------

def test_coverage_basic_counts():
    data = _sample_data()
    links = _sample_links()
    covered, total, pct = _coverage(data, links)
    assert covered == 1
    assert total == 2
    assert pct == 50.0


def test_coverage_zero_total_returns_zero_pct():
    data = ComplianceData(schema=default_schema())  # no requirements
    covered, total, pct = _coverage(data, [])
    assert (covered, total, pct) == (0, 0, 0.0)


# ----------------------------- report_markdown -----------------------------

def _render_markdown(tmp_path: Path, gaps: list[Gap],
                     data: ComplianceData = None,
                     links: list[TraceLink] = None,
                     repo: Path = None) -> str:
    output = tmp_path / "report.md"
    report_markdown(
        output=output,
        repo=repo or tmp_path,
        trace_links=links if links is not None else _sample_links(),
        data=data or _sample_data(),
        gaps=gaps,
    )
    return output.read_text(encoding="utf-8")


def test_markdown_includes_commit_hash_when_in_git_repo(tmp_path):
    md = _render_markdown(tmp_path, [], repo=Path(__file__).parent.parent)
    assert "**Commit:**" in md
    m = re.search(r"\*\*Commit:\*\* `([0-9a-f]+)`", md)
    assert m, "expected backticked SHA after **Commit:**"


def test_markdown_omits_commit_when_outside_git_repo(tmp_path):
    md = _render_markdown(tmp_path, [], repo=tmp_path)
    assert "**Commit:**" not in md


def test_markdown_contains_info_coverage_row_in_gaps_table(tmp_path):
    gap = Gap(severity="critical", rule_id="R-62304-NOT-IMPL",
              message="SR-2 — no code annotation found", node_id="SR-2",
              reference="IEC 62304 §5.3")
    md = _render_markdown(tmp_path, [gap])
    # INFO row appended to the gaps table — same column count.
    assert "| 🔵 INFO |" in md
    assert "1 / 2 SW requirements covered (50%)" in md
    # Old separate "## Coverage" section is no longer emitted.
    assert "## Coverage" not in md


def test_markdown_readiness_blocked_on_critical(tmp_path):
    gap = Gap(severity="critical", rule_id="R-62304-NOT-IMPL",
              message="x", reference="IEC 62304 §5.3")
    md = _render_markdown(tmp_path, [gap])
    assert "Submission readiness: BLOCKED" in md


def test_markdown_readiness_review_needed_on_warnings_only(tmp_path):
    gap = Gap(severity="warning", rule_id="R-62304-NO-CLASS",
              message="x", reference="IEC 62304 §4.3")
    md = _render_markdown(tmp_path, [gap])
    assert "Submission readiness: REVIEW NEEDED" in md


def test_markdown_readiness_clear_when_no_gaps(tmp_path):
    md = _render_markdown(tmp_path, [])
    assert "Submission readiness: CLEAR" in md


def test_markdown_table_row_count_matches_gaps_plus_one_info(tmp_path):
    """N gap rows + 1 INFO coverage row + 1 header + 1 separator."""
    gaps = [
        Gap(severity="critical", rule_id="R-A", message="msg1", reference="r1"),
        Gap(severity="warning", rule_id="R-B", message="msg2", reference="r2"),
    ]
    md = _render_markdown(tmp_path, gaps)
    table_lines = [l for l in md.splitlines() if l.startswith("|")]
    # 1 header + 1 separator + 2 gaps + 1 INFO row = 5
    assert len(table_lines) == 5, f"unexpected table:\n{chr(10).join(table_lines)}"


# ----------------------------- report_json -----------------------------

def test_json_contract_unchanged(tmp_path):
    gaps = [
        Gap(severity="critical", rule_id="R-62304-NOT-IMPL",
            message="missing", node_id="SR-1", reference="IEC 62304 §5.3",
            details={"k": "v"}),
    ]
    buf = io.StringIO()
    with redirect_stdout(buf):
        report_json(gaps)
    payload = json.loads(buf.getvalue())
    assert payload["total"] == 1
    assert payload["gaps"][0]["rule_id"] == "R-62304-NOT-IMPL"
    assert payload["gaps"][0]["details"] == {"k": "v"}
