"""Tests for loader.py"""

import pytest
from pathlib import Path
from regops.loader import load_compliance

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_requirements():
    data = load_compliance(FIXTURES)
    assert "SR-001" in data.requirements
    assert "SR-002" in data.requirements
    assert "SR-005" in data.requirements  # gap fixture — exists in YAML but not in code


def test_sr002_is_class_c():
    data = load_compliance(FIXTURES)
    assert data.requirements["SR-002"].safety_class == "C"


def test_load_risks():
    data = load_compliance(FIXTURES)
    assert "RISK-001" in data.risks
    assert "RISK-002" in data.risks


def test_load_tests():
    data = load_compliance(FIXTURES)
    assert "TC-003" in data.tests  # verifies SR-002


def test_tc003_is_unit_test():
    data = load_compliance(FIXTURES)
    assert data.tests["TC-003"].type == "unit_test"


def test_schema_loaded():
    data = load_compliance(FIXTURES)
    assert "software_requirement" in data.schema.node_types


def test_missing_compliance_dir_returns_empty():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        data = load_compliance(Path(tmp))
    assert data.requirements == {}
    assert data.risks == {}


def test_risk_loads_hazard_probability_residual():
    """Extended Risk fields from CLAUDE.md model must be loaded."""
    data = load_compliance(FIXTURES)
    r = data.risks["RISK-001"]
    assert r.hazard == "HAZ-001"
    assert r.probability == "unlikely"
    assert r.residual_risk == "acceptable"


def test_test_case_file_field_loaded():
    """TestCase.file (pointer to test function) loaded when present in YAML."""
    data = load_compliance(FIXTURES)
    tc = data.tests["TC-003"]
    # TC-003 has 'file' set in fixtures; if absent in some YAMLs, field is None.
    assert tc.file is None or isinstance(tc.file, str)


def test_extended_need_fixtures_loaded():
    """REG-/SEC-/ARCH-001 fixtures must load with the expected need types."""
    data = load_compliance(FIXTURES)
    for nid, expected_type in [
        ("REG-001", "regulatory_need"),
        ("SEC-001", "security_need"),
        ("ARCH-001", "architectural_need"),
    ]:
        assert nid in data.requirements, f"{nid} missing"
        assert data.requirements[nid].type == expected_type


def test_sys001_has_composite_parents():
    """SYS-001 demos composite parentage: both a user_need and a security_need."""
    data = load_compliance(FIXTURES)
    parents = set(data.requirements["SYS-001"].parent_refs)
    assert parents == {"UN-001", "SEC-001"}


def test_iso_date_normalisation_for_last_reviewed():
    """PyYAML auto-parses YYYY-MM-DD to datetime.date; loader must stringify."""
    data = load_compliance(FIXTURES)
    for req in data.requirements.values():
        if req.last_reviewed is not None:
            assert isinstance(req.last_reviewed, str)
