"""Tests for schema.py — meta-model loading and lookup."""

from pathlib import Path
import tempfile
import textwrap

import pytest

from regops.schema import (
    NodeType,
    Schema,
    default_schema,
    load_schema,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
FIXTURE_SCHEMA = FIXTURES / ".regops" / "schema.yaml"


def test_load_fixture_schema():
    schema = load_schema(FIXTURE_SCHEMA)
    assert "software_requirement" in schema.node_types
    assert schema.node_types["software_requirement"].abbreviation == "SR"
    assert schema.node_types["software_requirement"].requires_code is True
    assert schema.node_types["user_need"].requires_code is False


def test_types_with_maps_to():
    schema = load_schema(FIXTURE_SCHEMA)
    assert schema.types_with_maps_to("software_requirement") == {"software_requirement"}
    assert schema.types_with_maps_to("nonexistent") == set()


def test_active_standards_loaded():
    schema = load_schema(FIXTURE_SCHEMA)
    assert "iec_62304" in schema.active_standards
    assert "iso_14971" in schema.active_standards


def test_missing_file_returns_default():
    schema = load_schema(Path("/nonexistent/.regops/schema.yaml"))
    assert "software_requirement" in schema.node_types
    assert schema.node_types["software_requirement"].requires_code is True


def test_default_schema_parity_with_old_hardcoded_sets():
    """The default schema must cover the same SW-requirement types the
    old hardcoded sets did, so existing fixtures keep producing identical gaps."""
    schema = default_schema()
    sw_types: set[str] = set()
    for concept in ("software_requirement", "software_item", "software_unit"):
        sw_types |= schema.types_with_maps_to(concept)
    assert sw_types == {"software_requirement", "software_item", "software_unit"}


def test_custom_schema_with_renamed_type():
    """A client can rename SR to SW_REQ; rules must still detect it
    via maps_to: software_requirement."""
    yaml_text = textwrap.dedent("""
        node_types:
          sw_req:
            label: "Software Requirement"
            abbreviation: "SW"
            maps_to: software_requirement
            requires_code: true
    """)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        tmp = Path(f.name)
    try:
        schema = load_schema(tmp)
        assert schema.types_with_maps_to("software_requirement") == {"sw_req"}
        assert schema.requires_code("sw_req") is True
    finally:
        tmp.unlink()


def test_malformed_yaml_returns_default():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("this is :: not :: valid :: yaml ::: [")
        tmp = Path(f.name)
    try:
        schema = load_schema(tmp)
        assert schema.node_types == default_schema().node_types
    finally:
        tmp.unlink()


def test_empty_node_types_returns_default():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("active_standards: [iec_62304]\n")
        tmp = Path(f.name)
    try:
        schema = load_schema(tmp)
        assert "software_requirement" in schema.node_types
    finally:
        tmp.unlink()
