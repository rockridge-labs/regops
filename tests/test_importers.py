"""Tests for the importers package — registry, ABC contract, default to_compliance_yaml."""

from pathlib import Path

import pytest
import yaml

from regops.importers import (
    ImporterBase,
    ImportPayload,
    get_importer,
    list_importers,
    register,
)
from regops.importers import _REGISTRY
from regops.loader import load_compliance


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Isolate every test from registry pollution."""
    saved = dict(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(saved)


class _DummyImporter(ImporterBase):
    """Hand-rolled importer used to exercise the contract without I/O."""
    name = "dummy"

    def fetch(self, **kwargs) -> ImportPayload:
        return ImportPayload(
            requirements=[
                {"id": "SR-001", "type": "software_requirement",
                 "title": "Imported SR", "safety_class": "B",
                 "parent_refs": ["SYS-001"], "status": "draft"},
                {"id": "SYS-001", "type": "system_requirement",
                 "title": "Imported SYS", "parent_refs": ["UN-001"]},
                {"id": "UN-001", "type": "user_need", "title": "Imported UN"},
            ],
            risks=[
                {"id": "RISK-001", "title": "Imported risk",
                 "severity": "minor", "mitigation_refs": ["MIT-001"]},
            ],
            tests=[
                {"id": "TC-001", "title": "Imported test",
                 "type": "unit_test", "verifies_refs": ["SR-001"]},
            ],
            source_name="dummy",
            source_metadata={"version": "test"},
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_register_adds_importer_to_registry():
    register(_DummyImporter)
    assert "dummy" in list_importers()


def test_get_importer_returns_class():
    register(_DummyImporter)
    cls = get_importer("dummy")
    assert cls is _DummyImporter


def test_get_importer_unknown_name_raises_keyerror_with_available():
    with pytest.raises(KeyError) as excinfo:
        get_importer("does-not-exist")
    assert "Unknown importer" in str(excinfo.value)


def test_register_rejects_class_without_name():
    class Unnamed(ImporterBase):
        def fetch(self, **kwargs):
            return ImportPayload()
    with pytest.raises(ValueError, match="missing or empty `name`"):
        register(Unnamed)


def test_register_rejects_duplicate_name_from_different_class():
    register(_DummyImporter)

    class OtherDummy(ImporterBase):
        name = "dummy"
        def fetch(self, **kwargs):
            return ImportPayload()

    with pytest.raises(ValueError, match="already registered"):
        register(OtherDummy)


def test_register_is_idempotent_for_same_class():
    register(_DummyImporter)
    register(_DummyImporter)  # re-registering the same class is OK
    assert list_importers().count("dummy") == 1


# ---------------------------------------------------------------------------
# ABC contract
# ---------------------------------------------------------------------------

def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        ImporterBase()  # fetch() not implemented


def test_default_discover_returns_empty_dict():
    register(_DummyImporter)
    assert _DummyImporter().discover() == {}


# ---------------------------------------------------------------------------
# Default to_compliance_yaml — exercises the round-trip importer → loader
# ---------------------------------------------------------------------------

def test_to_compliance_yaml_writes_layout(tmp_path):
    importer = _DummyImporter()
    payload = importer.fetch()
    written = importer.to_compliance_yaml(payload, tmp_path)

    rel = sorted(p.relative_to(tmp_path).as_posix() for p in written)
    assert rel == [
        "compliance/requirements/SR-001.yaml",
        "compliance/requirements/SYS-001.yaml",
        "compliance/requirements/UN-001.yaml",
        "compliance/risks/RISK-001.yaml",
        "compliance/tests/TC-001.yaml",
    ]


def test_to_compliance_yaml_output_is_valid_yaml(tmp_path):
    importer = _DummyImporter()
    importer.to_compliance_yaml(importer.fetch(), tmp_path)
    sr = yaml.safe_load(
        (tmp_path / "compliance" / "requirements" / "SR-001.yaml").read_text()
    )
    assert sr["id"] == "SR-001"
    assert sr["safety_class"] == "B"


def test_to_compliance_yaml_round_trip_through_loader(tmp_path):
    """Files written by an importer must be loadable by regops.loader unchanged."""
    importer = _DummyImporter()
    importer.to_compliance_yaml(importer.fetch(), tmp_path)
    data = load_compliance(tmp_path)
    assert "SR-001" in data.requirements
    assert "RISK-001" in data.risks
    assert "TC-001" in data.tests
    assert data.requirements["SR-001"].safety_class == "B"


def test_to_compliance_yaml_skips_items_without_id(tmp_path):
    class NoIdImporter(ImporterBase):
        name = "noid"
        def fetch(self, **kwargs):
            return ImportPayload(requirements=[
                {"id": "SR-1", "type": "software_requirement", "title": "ok"},
                {"type": "software_requirement", "title": "no id"},
            ])
    importer = NoIdImporter()
    written = importer.to_compliance_yaml(importer.fetch(), tmp_path)
    assert len(written) == 1


def test_to_compliance_yaml_skips_empty_buckets(tmp_path):
    class OnlyReqs(ImporterBase):
        name = "onlyreqs"
        def fetch(self, **kwargs):
            return ImportPayload(requirements=[
                {"id": "SR-1", "type": "software_requirement", "title": "ok"},
            ])
    importer = OnlyReqs()
    importer.to_compliance_yaml(importer.fetch(), tmp_path)
    assert not (tmp_path / "compliance" / "risks").exists()
    assert not (tmp_path / "compliance" / "tests").exists()
