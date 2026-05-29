"""Tests for checker.py — gap detection engine."""

import pytest
from pathlib import Path
from regops.parser import parse_repo, TraceLink
from regops.loader import (
    ComplianceData,
    Requirement,
    load_compliance,
)
from regops.checker import check_traceability
from regops.schema import NodeType, Schema

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


def test_mit_orphan_detected_on_mit_999(gaps):
    """MIT-999 is annotated in signal.py but absent from all risk files
    → must trigger R-14971-MIT-ORPHAN."""
    orphans = [g for g in gaps if g.rule_id == "R-14971-MIT-ORPHAN"]
    node_ids = [g.node_id for g in orphans]
    assert "MIT-999" in node_ids, f"Expected MIT-999 in {node_ids}"


def test_mit_orphan_does_not_trigger_for_declared_mitigations(gaps):
    """MIT-001..MIT-004 are declared in some risk's mitigation_refs
    → must NOT trigger R-14971-MIT-ORPHAN."""
    orphans = [g for g in gaps if g.rule_id == "R-14971-MIT-ORPHAN"]
    node_ids = {g.node_id for g in orphans}
    declared = {"MIT-001", "MIT-002", "MIT-003", "MIT-004"}
    assert not (declared & node_ids), \
        f"Declared mitigations falsely flagged as orphan: {declared & node_ids}"


def test_class_b_test_rule_uses_iec_62304_5_5_2():
    """R-62304-CLASS-B-TEST normative reference must be aligned with CLAUDE.md (§5.5.2)."""
    from regops.checker import RULE_REFERENCE
    assert RULE_REFERENCE["R-62304-CLASS-B-TEST"] == "IEC 62304 §5.5.2"


def test_orphan_req_uses_tracability_category():
    """R-TRACE-ORPHAN-REQ category must be 'Traçabilité' per CLAUDE.md ligne 245."""
    from regops.checker import RULE_REFERENCE
    assert RULE_REFERENCE["R-TRACE-ORPHAN-REQ"] == "Traçabilité"


def test_rule_severity_is_central_source_of_truth():
    """All eight V1 rules must have an entry in RULE_SEVERITY."""
    from regops.checker import RULE_SEVERITY
    expected = {
        "R-62304-NOT-IMPL", "R-62304-NO-CLASS",
        "R-62304-CLASS-C-TEST", "R-62304-CLASS-B-TEST",
        "R-14971-RISK-NO-MIT", "R-14971-MIT-ORPHAN",
        "R-TRACE-ORPHAN-REQ", "R-TRACE-NO-PARENT",
    }
    assert set(RULE_SEVERITY) == expected


def test_custom_schema_renamed_type_triggers_not_impl():
    """A client schema renames `software_requirement` → `sw_req`.
    A SR-xxx with type=sw_req must still produce R-62304-NOT-IMPL if not
    referenced in code — proving the checker honours `maps_to`, not the type label."""
    schema = Schema(node_types={
        "sw_req": NodeType(
            name="sw_req",
            label="Software Requirement",
            abbreviation="SW",
            maps_to="software_requirement",
            requires_code=True,
        ),
    })
    data = ComplianceData(
        requirements={
            "SR-100": Requirement(
                id="SR-100",
                type="sw_req",          # the client's custom type name
                title="Custom-typed requirement",
                safety_class="B",
                parent_refs=["SYS-001"],
            ),
        },
        schema=schema,
    )
    gaps = check_traceability(data, trace_links=[])
    not_impl = [g for g in gaps if g.rule_id == "R-62304-NOT-IMPL"]
    assert "SR-100" in [g.node_id for g in not_impl]
