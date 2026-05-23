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
    assert "node_types" in data.schema


def test_missing_compliance_dir_returns_empty():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        data = load_compliance(Path(tmp))
    assert data.requirements == {}
    assert data.risks == {}
