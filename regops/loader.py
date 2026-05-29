"""
loader.py
Load compliance YAML files from the repository.

Expected structure:
  compliance/
    requirements/   SR-xxx.yaml, SYS-xxx.yaml, UN-xxx.yaml ...
    risks/          RISK-xxx.yaml ...
    tests/          TC-xxx.yaml ...
  .regops/
    schema.yaml
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml

from regops.schema import Schema, load_schema


@dataclass
class Requirement:
    id: str
    type: str                               # software_requirement, user_need, etc.
    title: str
    description: str = ""
    safety_class: Optional[str] = None     # A | B | C | None
    parent_refs: list[str] = field(default_factory=list)
    risk_refs: list[str] = field(default_factory=list)
    test_refs: list[str] = field(default_factory=list)
    status: str = "draft"


@dataclass
class Risk:
    id: str
    title: str
    severity: str                           # critical | major | minor
    mitigation_refs: list[str] = field(default_factory=list)
    status: str = "draft"


@dataclass
class TestCase:
    id: str
    title: str
    type: str                               # unit_test | integration_test | system_test | validation
    verifies_refs: list[str] = field(default_factory=list)
    regression: bool = False
    last_result: Optional[str] = None      # passed | failed | not_run | None


@dataclass
class ComplianceData:
    requirements: dict[str, Requirement] = field(default_factory=dict)
    risks: dict[str, Risk] = field(default_factory=dict)
    tests: dict[str, TestCase] = field(default_factory=dict)
    schema: Schema = field(default_factory=Schema)


def load_compliance(root: Path) -> ComplianceData:
    """Load all compliance YAML files from repo root."""
    data = ComplianceData()

    compliance_dir = root / "compliance"
    schema_path = root / ".regops" / "schema.yaml"

    # Load schema (built-in default if file missing or malformed)
    data.schema = load_schema(schema_path)

    # Load requirements
    req_dir = compliance_dir / "requirements"
    if req_dir.exists():
        for f in sorted(req_dir.glob("*.yaml")):
            raw = _load_yaml(f)
            if raw and "id" in raw:
                req = Requirement(
                    id=raw["id"],
                    type=raw.get("type", "software_requirement"),
                    title=raw.get("title", ""),
                    description=raw.get("description", ""),
                    safety_class=raw.get("safety_class"),
                    parent_refs=raw.get("parent_refs", []),
                    risk_refs=raw.get("risk_refs", []),
                    test_refs=raw.get("test_refs", []),
                    status=raw.get("status", "draft"),
                )
                data.requirements[req.id] = req

    # Load risks
    risk_dir = compliance_dir / "risks"
    if risk_dir.exists():
        for f in sorted(risk_dir.glob("*.yaml")):
            raw = _load_yaml(f)
            if raw and "id" in raw:
                risk = Risk(
                    id=raw["id"],
                    title=raw.get("title", ""),
                    severity=raw.get("severity", "minor"),
                    mitigation_refs=raw.get("mitigation_refs", []),
                    status=raw.get("status", "draft"),
                )
                data.risks[risk.id] = risk

    # Load tests
    test_dir = compliance_dir / "tests"
    if test_dir.exists():
        for f in sorted(test_dir.glob("*.yaml")):
            raw = _load_yaml(f)
            if raw and "id" in raw:
                tc = TestCase(
                    id=raw["id"],
                    title=raw.get("title", ""),
                    type=raw.get("type", "unit_test"),
                    verifies_refs=raw.get("verifies_refs", []),
                    regression=raw.get("regression", False),
                    last_result=raw.get("last_result"),
                )
                data.tests[tc.id] = tc

    return data


def _load_yaml(path: Path) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None
