"""Tests for checker.py — gap detection engine."""

import pytest
from pathlib import Path
from regops.parser import parse_repo
from regops.loader import load_compliance
from regops.checker import check_traceability

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="module")
def gaps():
    links = parse_repo(FIXTURES)
    data = load_compliance(FIXTURES)
    return check_traceability(data, links)


def test_sr005_not_implemented_gap(gaps):
    """SR-005 (alarm) has no code annotation — should be critical gap."""
    not_impl = [g for g in gaps if g.rule_id == "R-62304-NOT-IMPL"]
    node_ids = [g.node_id for g in not_impl]
    assert "SR-005" in node_ids, f"Expected SR-005 in NOT-IMPL gaps, got: {node_ids}"


def test_no_false_positive_sr001(gaps):
    """SR-001 IS annotated — should NOT appear in NOT-IMPL gaps."""
    not_impl_ids = [g.node_id for g in gaps if g.rule_id == "R-62304-NOT-IMPL"]
    assert "SR-001" not in not_impl_ids


def test_critical_gaps_sorted_first(gaps):
    """Critical gaps should appear before warnings."""
    severities = [g.severity for g in gaps]
    last_critical = max((i for i, s in enumerate(severities) if s == "critical"), default=-1)
    first_warning = min((i for i, s in enumerate(severities) if s == "warning"), default=len(severities))
    assert last_critical < first_warning, "Critical gaps should come before warnings"


def test_mitigation_gaps_detected(gaps):
    """MIT-xxx annotations missing in code should be detected."""
    mit_gaps = [g for g in gaps if g.rule_id == "R-14971-RISK-NO-MIT"]
    assert len(mit_gaps) > 0, "Expected at least one mitigation gap (fixtures use MIT-xxx not annotated)"


def test_all_gaps_have_rule_id(gaps):
    """Every gap must have a rule_id."""
    assert all(g.rule_id for g in gaps)


def test_all_gaps_have_message(gaps):
    """Every gap must have a non-empty message."""
    assert all(g.message for g in gaps)
