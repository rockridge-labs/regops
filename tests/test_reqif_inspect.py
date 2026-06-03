"""Tests for `regops reqif inspect` — parser + skeleton emission + .reqifz reject."""

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from regops.reqif import parse_reqif, run_inspect
from regops.reqif.inspect import REQIFZ_REJECT_MSG


FIXTURES = Path(__file__).parent.parent / "fixtures" / "reqif"


def _capture(file_path: Path, output_skeleton: Path = None) -> tuple[int, str]:
    """Run inspect, capture all Rich output as plain text."""
    buf = StringIO()
    console = Console(file=buf, width=160, no_color=True, legacy_windows=False)
    rc = run_inspect(console, file_path, output_skeleton)
    return rc, buf.getvalue()


# ---------------------------------------------------------------------------
# Parser — multi-types fixture
# ---------------------------------------------------------------------------

def test_multi_types_lists_three_distinct_spec_object_types():
    content = parse_reqif(FIXTURES / "multi_types.reqif")
    assert set(content.spec_object_types) == {"SOT_UN", "SOT_SR", "SOT_TC"}
    assert content.spec_object_types["SOT_UN"].long_name == "User Story"
    assert content.spec_object_types["SOT_SR"].long_name == "Software Requirement"


def test_multi_types_attributes_carry_datatype():
    content = parse_reqif(FIXTURES / "multi_types.reqif")
    sr = content.spec_object_types["SOT_SR"]
    by_name = {a.long_name: a.datatype for a in sr.attributes}
    assert by_name == {"title": "STRING", "priority": "ENUMERATION"}


def test_multi_types_counts_objects_per_type():
    content = parse_reqif(FIXTURES / "multi_types.reqif")
    type_refs = [so.type_ref for so in content.spec_objects]
    assert type_refs.count("SOT_UN") == 1
    assert type_refs.count("SOT_SR") == 2
    assert type_refs.count("SOT_TC") == 1


# ---------------------------------------------------------------------------
# Parser — relations fixture
# ---------------------------------------------------------------------------

def test_with_relations_lists_two_relation_types():
    content = parse_reqif(FIXTURES / "with_relations.reqif")
    assert set(content.spec_relation_types) == {"SRT_DERIVES", "SRT_VERIFIES"}
    assert len(content.spec_relations) == 3


def test_with_relations_records_source_target_type():
    content = parse_reqif(FIXTURES / "with_relations.reqif")
    rels = {r.identifier: r for r in content.spec_relations}
    assert rels["SR_REL_1"].type_ref == "SRT_DERIVES"
    assert rels["SR_REL_1"].source_ref == "SO_R2"
    assert rels["SR_REL_1"].target_ref == "SO_R1"


# ---------------------------------------------------------------------------
# Parser — incomplete schema must NOT crash
# ---------------------------------------------------------------------------

def test_incomplete_schema_does_not_crash_and_collects_warnings():
    content = parse_reqif(FIXTURES / "incomplete_schema.reqif")
    # No raise. Warnings present.
    assert content.warnings, "expected warnings for incomplete schema"
    # The typed SO is found, the untyped one too (with type_ref=None).
    by_id = {so.identifier: so for so in content.spec_objects}
    assert by_id["SO_TYPED"].type_ref == "SOT_NAMELESS"
    assert by_id["SO_UNTYPED"].type_ref is None
    # SPEC-OBJECT without identifier is skipped (and warned).
    assert all(so.identifier for so in content.spec_objects)
    # SPEC-OBJECT-TYPE without identifier is also skipped.
    assert all(sot.identifier for sot in content.spec_object_types.values())


# ---------------------------------------------------------------------------
# Parser — DOORS indirect typing
# ---------------------------------------------------------------------------

def test_doors_indirect_type_resolves_via_spec_hierarchy():
    content = parse_reqif(FIXTURES / "doors_indirect_type.reqif")
    by_id = {so.identifier: so for so in content.spec_objects}
    assert by_id["SO_INDIRECT_001"].type_ref == "SOT_DOORS_REQ"
    assert by_id["SO_INDIRECT_001"].inferred_from_hierarchy is True
    assert by_id["SO_INDIRECT_002"].type_ref == "SOT_DOORS_REQ"


# ---------------------------------------------------------------------------
# CLI — .reqifz reject
# ---------------------------------------------------------------------------

def test_reqifz_is_rejected_with_exit_code_2():
    rc, output = _capture(FIXTURES / "fake.reqifz")
    assert rc == 2
    # Compare on first line only — Rich may wrap the rest.
    assert REQIFZ_REJECT_MSG.splitlines()[0] in output


def test_reqifz_is_detected_by_extension_only():
    """Renaming a real .reqif to .reqifz must still trigger the reject path
    (the question 5 answer was 'extension', not magic-byte detection)."""
    # Use the multi_types.reqif content but address it via a .reqifz extension.
    tmp = FIXTURES / "_renamed_alias.reqifz"
    try:
        tmp.write_bytes((FIXTURES / "multi_types.reqif").read_bytes())
        rc, _ = _capture(tmp)
        assert rc == 2
    finally:
        if tmp.exists():
            tmp.unlink()


# ---------------------------------------------------------------------------
# Inspect — happy path
# ---------------------------------------------------------------------------

def test_inspect_returns_zero_and_prints_skeleton_to_stdout(capsys):
    rc, output = _capture(FIXTURES / "multi_types.reqif")
    assert rc == 0
    assert "import_mapping:" in output
    assert "reqif:" in output
    assert "spec_object_types:" in output
    # Empty values, never guessed.
    assert '"User Story": ""' in output
    assert '"Software Requirement": ""' in output


def test_inspect_skeleton_includes_object_count_per_type():
    _, output = _capture(FIXTURES / "multi_types.reqif")
    # SOT_SR has 2 objects.
    assert "2 objects" in output or "2 object" in output


def test_inspect_skeleton_includes_warning_header():
    _, output = _capture(FIXTURES / "multi_types.reqif")
    assert "WARNING" in output
    assert "intentionally empty" in output


def test_inspect_with_output_skeleton_writes_file(tmp_path):
    target = tmp_path / "skel.yaml"
    rc, output = _capture(FIXTURES / "with_relations.reqif", target)
    assert rc == 0
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "spec_relation_types:" in content
    assert '"derivesFrom": ""' in content
    assert '"verifiedBy": ""' in content
    # When --output-skeleton is used, the skeleton is NOT echoed to stdout.
    assert '"derivesFrom": ""' not in output


def test_inspect_no_relations_emits_empty_dict_marker():
    _, output = _capture(FIXTURES / "multi_types.reqif")
    assert "no SPEC-RELATION-TYPE present" in output
