"""Tests for the `regops init` bootstrap workflow."""

from pathlib import Path

import pytest

from regops.bootstrap import bootstrap_repo, TEMPLATE_TARGETS
from regops.loader import load_compliance


def test_bootstrap_creates_all_expected_files(tmp_path):
    created = bootstrap_repo(tmp_path)
    expected = {tmp_path / rel for rel in TEMPLATE_TARGETS.values()}
    assert set(created) == expected
    for f in expected:
        assert f.exists() and f.read_text(encoding="utf-8").strip(), f"{f} empty or missing"


def test_bootstrap_refuses_overwrite_by_default(tmp_path):
    bootstrap_repo(tmp_path)
    with pytest.raises(FileExistsError):
        bootstrap_repo(tmp_path)


def test_bootstrap_force_overwrites(tmp_path):
    first = bootstrap_repo(tmp_path)
    second = bootstrap_repo(tmp_path, force=True)
    assert set(first) == set(second)


def test_bootstrap_applies_safety_class(tmp_path):
    bootstrap_repo(tmp_path, safety_class="C")
    sr_content = (tmp_path / "compliance" / "requirements" / "SR-001.yaml").read_text(encoding="utf-8")
    schema_content = (tmp_path / ".regops" / "schema.yaml").read_text(encoding="utf-8")
    assert "safety_class: C" in sr_content
    assert "safety_class: C" in schema_content


def test_bootstrap_applies_standard(tmp_path):
    bootstrap_repo(tmp_path, standard="iso14971")
    schema_content = (tmp_path / ".regops" / "schema.yaml").read_text(encoding="utf-8")
    assert "- iso_14971" in schema_content


def test_bootstrap_unknown_standard_passes_through(tmp_path):
    bootstrap_repo(tmp_path, standard="custom_std")
    schema_content = (tmp_path / ".regops" / "schema.yaml").read_text(encoding="utf-8")
    assert "- custom_std" in schema_content


def test_bootstrap_output_is_loadable_by_loader(tmp_path):
    """The bootstrapped repo must parse cleanly with regops.loader — closes
    the loop between init and check on the same fresh tree."""
    bootstrap_repo(tmp_path)
    data = load_compliance(tmp_path)
    assert "UN-001" in data.requirements
    assert "SYS-001" in data.requirements
    assert "SR-001" in data.requirements
    assert "RISK-001" in data.risks
    assert "TC-001" in data.tests
    assert data.schema.node_types["software_requirement"].requires_code is True


def test_bootstrap_creates_extended_need_files(tmp_path):
    """The init scaffold must include REG/SEC/ARCH need examples so users
    discover the extended taxonomy without reading docs first."""
    bootstrap_repo(tmp_path)
    reqs_dir = tmp_path / "compliance" / "requirements"
    for name in ("REG-001.yaml", "SEC-001.yaml", "ARCH-001.yaml"):
        assert (reqs_dir / name).exists(), f"missing {name}"


def test_bootstrap_no_unresolved_placeholders(tmp_path):
    bootstrap_repo(tmp_path)
    for rel in TEMPLATE_TARGETS.values():
        content = (tmp_path / rel).read_text(encoding="utf-8")
        assert "{{" not in content and "}}" not in content, \
            f"Unresolved placeholder in {rel}"
