"""
schema.py
Configurable meta-model for compliance node types.

A project's .regops/schema.yaml declares its own node types (terminology)
and maps each to a standard concept (`maps_to`). Compliance rules operate
on the standard concept, never on the local label — so a client can rename
"software_requirement" to "SW_REQ" without changing the rule engine.

Fallback: if no schema file exists, a built-in default schema mirroring the
IEC 62304 standard taxonomy is used. This keeps the tool usable on repos
that haven't run `regops init` yet.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class NodeType:
    """A single node type declared in .regops/schema.yaml."""
    name: str                          # key in node_types: dict (e.g. "software_requirement")
    label: str                         # human-readable label
    abbreviation: str                  # ID prefix (e.g. "SR")
    maps_to: str                       # standard concept (e.g. "software_requirement")
    requires_code: bool = False        # must be referenced in source code


@dataclass
class Schema:
    """Loaded compliance schema. Indexed by node type name."""
    node_types: dict[str, NodeType] = field(default_factory=dict)
    active_standards: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)    # full YAML for downstream access

    def types_with_maps_to(self, concept: str) -> set[str]:
        """Return the set of node-type names mapping to a given standard concept."""
        return {nt.name for nt in self.node_types.values() if nt.maps_to == concept}

    def requires_code(self, type_name: str) -> bool:
        """Whether a node type requires a code annotation."""
        nt = self.node_types.get(type_name)
        return nt.requires_code if nt else False


# Built-in default schema — used when no .regops/schema.yaml is present.
# Mirrors the IEC 62304 standard taxonomy so existing fixtures keep working.
_DEFAULT_NODE_TYPES = [
    NodeType("user_need",            "User Need",            "UN",  "user_need",            False),
    NodeType("system_requirement",   "System Requirement",   "SYS", "system_requirement",   False),
    NodeType("software_requirement", "Software Requirement", "SR",  "software_requirement", True),
    NodeType("software_item",        "Software Item",        "SI",  "software_item",        True),
    NodeType("software_unit",        "Software Unit",        "SU",  "software_unit",        True),
]


def default_schema() -> Schema:
    """Return the built-in fallback schema."""
    return Schema(
        node_types={nt.name: nt for nt in _DEFAULT_NODE_TYPES},
        active_standards=["iec_62304", "iso_14971"],
    )


def load_schema(path: Path) -> Schema:
    """
    Load a schema from .regops/schema.yaml.
    Returns the default schema if the file is missing, empty, or malformed.
    """
    if not path.exists():
        return default_schema()

    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return default_schema()

    raw_types = raw.get("node_types") or {}
    if not isinstance(raw_types, dict) or not raw_types:
        return default_schema()

    node_types: dict[str, NodeType] = {}
    for name, body in raw_types.items():
        if not isinstance(body, dict):
            continue
        node_types[name] = NodeType(
            name=name,
            label=body.get("label", name),
            abbreviation=body.get("abbreviation", ""),
            maps_to=body.get("maps_to", name),
            requires_code=bool(body.get("requires_code", False)),
        )

    if not node_types:
        return default_schema()

    return Schema(
        node_types=node_types,
        active_standards=list(raw.get("active_standards") or []),
        raw=raw,
    )
