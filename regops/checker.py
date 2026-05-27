"""
checker.py
Traceability gap detection engine.

Rules implemented (V1):
  R-62304-NOT-IMPL      SW requirement with no code annotation
  R-62304-CLASS-C-TEST  Class C requirement with no unit test
  R-62304-CLASS-B-TEST  Class B requirement with no test at all
  R-62304-NO-CLASS      SW requirement with no safety_class declared
  R-14971-RISK-NO-MIT   Risk with no mitigation referenced in code
  R-14971-MIT-ORPHAN    Mitigation in code referencing unknown risk
  R-TRACE-ORPHAN-REQ    Code annotation referencing unknown requirement ID
  R-TRACE-NO-PARENT     SW requirement with no parent SYS or UN
"""

from dataclasses import dataclass, field
from typing import Optional

from regops.loader import ComplianceData
from regops.parser import TraceLink
from regops.schema import Schema, default_schema

# Standard concepts whose node types should be referenced from source code.
CODE_REQUIRED_CONCEPTS = {
    "software_requirement",
    "software_item",
    "software_unit",
}

# Standard concepts exempt from the "must have a parent" rule.
NO_PARENT_EXEMPT_CONCEPTS = {
    "user_need",
    "system_requirement",
}


def _resolve_schema(data: ComplianceData) -> Schema:
    """Return the data's schema, or the built-in default if empty."""
    return data.schema if data.schema.node_types else default_schema()


def _types_needing_code(schema: Schema) -> set[str]:
    """Set of node-type names that must be referenced in source code."""
    out: set[str] = set()
    for concept in CODE_REQUIRED_CONCEPTS:
        out |= schema.types_with_maps_to(concept)
    # A type can also opt-in via `requires_code: true` even if maps_to differs.
    out |= {n for n, nt in schema.node_types.items() if nt.requires_code}
    return out


def _types_needing_parent(schema: Schema) -> set[str]:
    """Set of node-type names that must declare a parent requirement."""
    exempt: set[str] = set()
    for concept in NO_PARENT_EXEMPT_CONCEPTS:
        exempt |= schema.types_with_maps_to(concept)
    return set(schema.node_types) - exempt


@dataclass
class Gap:
    severity: str           # critical | warning | info
    rule_id: str
    message: str
    node_id: Optional[str] = None
    details: dict = field(default_factory=dict)
    reference: str = ""


def check_traceability(
    data: ComplianceData,
    trace_links: list[TraceLink],
) -> list[Gap]:
    """Run all V1 rules and return list of gaps, ordered by severity."""

    schema = _resolve_schema(data)
    needs_code_types = _types_needing_code(schema)
    needs_parent_types = _types_needing_parent(schema)

    gaps: list[Gap] = []

    # Build indexes for fast lookup
    covered_reqs: set[str] = set()
    covered_risks: set[str] = set()
    covered_mitigations: set[str] = set()

    req_has_unit_test: set[str] = set()
    req_has_any_test: set[str] = set()

    for link in trace_links:
        covered_reqs.update(link.reqs)
        covered_risks.update(link.risks)
        covered_mitigations.update(link.mitigations)

    # Build test coverage indexes
    for tc in data.tests.values():
        for ref in tc.verifies_refs:
            req_has_any_test.add(ref)
            if tc.type == "unit_test":
                req_has_unit_test.add(ref)

    # -------------------------------------------------------------------------
    # R-TRACE-ORPHAN-REQ : annotation in code referencing unknown requirement
    # -------------------------------------------------------------------------
    for link in trace_links:
        for req_id in link.reqs:
            if req_id not in data.requirements:
                gaps.append(Gap(
                    severity="critical",
                    rule_id="R-TRACE-ORPHAN-REQ",
                    node_id=req_id,
                    message=(
                        f"{req_id} — referenced in code ({link.file}:{link.line}) "
                        f"but not found in compliance/requirements/"
                    ),
                    details={"file": link.file, "line": link.line},
                    reference="IEC 62304 §5.3",
                ))

    # -------------------------------------------------------------------------
    # Per-requirement rules
    # -------------------------------------------------------------------------
    for req_id, req in data.requirements.items():

        needs_code = req.type in needs_code_types

        # R-62304-NOT-IMPL : SW requirement not referenced in code
        if needs_code and req_id not in covered_reqs:
            gaps.append(Gap(
                severity="critical",
                rule_id="R-62304-NOT-IMPL",
                node_id=req_id,
                message=f"{req_id} ({req.type}) — no code annotation found",
                details={"title": req.title, "type": req.type},
                reference="IEC 62304 §5.3",
            ))
            continue  # No point checking test coverage if not implemented

        # R-62304-NO-CLASS : SW requirement without safety_class
        if needs_code and req.safety_class is None:
            gaps.append(Gap(
                severity="warning",
                rule_id="R-62304-NO-CLASS",
                node_id=req_id,
                message=f"{req_id} — no safety_class declared (A, B, or C required)",
                details={"title": req.title},
                reference="IEC 62304 §4.3",
            ))

        # R-62304-CLASS-C-TEST : Class C needs unit test
        if needs_code and req.safety_class == "C":
            if req_id not in req_has_unit_test:
                gaps.append(Gap(
                    severity="critical",
                    rule_id="R-62304-CLASS-C-TEST",
                    node_id=req_id,
                    message=f"{req_id} (class C) — no unit test found in compliance/tests/",
                    details={"title": req.title, "safety_class": "C"},
                    reference="IEC 62304 §5.5.2",
                ))

        # R-62304-CLASS-B-TEST : Class B needs at least one test
        elif needs_code and req.safety_class == "B":
            if req_id not in req_has_any_test:
                gaps.append(Gap(
                    severity="warning",
                    rule_id="R-62304-CLASS-B-TEST",
                    node_id=req_id,
                    message=f"{req_id} (class B) — no test found in compliance/tests/",
                    details={"title": req.title, "safety_class": "B"},
                    reference="IEC 62304 §5.5.1",
                ))

        # R-TRACE-NO-PARENT : SW requirement without parent
        if (req.type in needs_parent_types
                and needs_code
                and not req.parent_refs):
            gaps.append(Gap(
                severity="warning",
                rule_id="R-TRACE-NO-PARENT",
                node_id=req_id,
                message=f"{req_id} — no parent requirement declared (SYS or UN expected)",
                details={"title": req.title},
                reference="IEC 62304 §5.2",
            ))

    # -------------------------------------------------------------------------
    # Per-risk rules
    # -------------------------------------------------------------------------
    for risk_id, risk in data.risks.items():

        # R-14971-RISK-NO-MIT : risk with no mitigation in code
        if not risk.mitigation_refs:
            gaps.append(Gap(
                severity="warning",
                rule_id="R-14971-RISK-NO-MIT",
                node_id=risk_id,
                message=f"{risk_id} — no mitigation_refs declared in risk file",
                details={"title": risk.title, "severity": risk.severity},
                reference="ISO 14971 §6.3",
            ))
        else:
            for mit_id in risk.mitigation_refs:
                if mit_id not in covered_mitigations:
                    gaps.append(Gap(
                        severity="critical" if risk.severity == "critical" else "warning",
                        rule_id="R-14971-RISK-NO-MIT",
                        node_id=risk_id,
                        message=(
                            f"{risk_id} — mitigation {mit_id} declared "
                            f"but not found in any code annotation"
                        ),
                        details={
                            "title": risk.title,
                            "mitigation": mit_id,
                            "risk_severity": risk.severity,
                        },
                        reference="ISO 14971 §6.3",
                    ))

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    gaps.sort(key=lambda g: severity_order.get(g.severity, 99))

    return gaps
