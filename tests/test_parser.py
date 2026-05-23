"""Tests for parser.py"""

import pytest
from pathlib import Path
from regops.parser import parse_repo, TraceLink

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_fixtures_returns_links():
    """Parser should find annotations in all fixture source files."""
    links = parse_repo(FIXTURES)
    assert len(links) > 0, "Expected at least one TraceLink from fixtures"


def test_parse_finds_sr002_in_cpp():
    """SR-002 should be found in calibration.cpp."""
    links = parse_repo(FIXTURES)
    req_ids = {req for link in links for req in link.reqs}
    assert "SR-002" in req_ids, "SR-002 not found in fixtures"


def test_parse_finds_sr001_in_python():
    """SR-001 should be found in signal.py."""
    links = parse_repo(FIXTURES)
    req_ids = {req for link in links for req in link.reqs}
    assert "SR-001" in req_ids


def test_parse_finds_sr003_in_go():
    """SR-003 should be found in dicom.go."""
    links = parse_repo(FIXTURES)
    req_ids = {req for link in links for req in link.reqs}
    assert "SR-003" in req_ids


def test_parse_finds_sr004_in_dart():
    """SR-004 should be found in ui.dart."""
    links = parse_repo(FIXTURES)
    req_ids = {req for link in links for req in link.reqs}
    assert "SR-004" in req_ids


def test_sr005_not_in_annotations():
    """SR-005 (alarm) is intentionally not annotated — gap fixture."""
    links = parse_repo(FIXTURES)
    req_ids = {req for link in links for req in link.reqs}
    assert "SR-005" not in req_ids, "SR-005 should NOT be in code (gap fixture)"


def test_safety_class_detected():
    """Safety class C should be detected on SR-002."""
    links = parse_repo(FIXTURES)
    class_c_links = [l for l in links if l.safety_class == "C"]
    assert len(class_c_links) > 0


def test_risk_annotations_detected():
    """Risk annotations should be found."""
    links = parse_repo(FIXTURES)
    risk_ids = {risk for link in links for risk in link.risks}
    assert "RISK-002" in risk_ids


def test_parse_inline_python():
    """Unit test: parse a string of Python code directly."""
    import tempfile, os
    code = "# @req SR-999 @risk RISK-999 @class B\ndef foo(): pass\n"
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = Path(f.name)
    try:
        links = parse_repo(tmp.parent)
        req_ids = {r for l in links for r in l.reqs}
        assert "SR-999" in req_ids
    finally:
        os.unlink(tmp)
