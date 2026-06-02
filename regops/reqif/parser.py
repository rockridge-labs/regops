"""
parser.py
Defensive XML parser for ReqIF 1.0.1 / 1.1 / 1.2.

Read-only. Returns a ReqIFContent dataclass — what is actually present
in the file. The parser:
  - never crashes on missing optional elements (collects warnings)
  - records the SPEC-OBJECT-TYPE of each item, falling back to the
    SpecHierarchy tree when the SPEC-OBJECT itself omits its <TYPE>
    (DOORS exports often do this)
  - does not interpret semantics — that is the job of the human-
    validated mapping a downstream import phase will consume.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Versions 1.0.1 / 1.1 / 1.2 share this namespace.
NS = {"r": "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"}


@dataclass
class AttributeDefinition:
    identifier: str
    long_name: str
    datatype: str  # STRING | INTEGER | ENUMERATION | BOOLEAN | DATE | REAL | XHTML | UNKNOWN


@dataclass
class SpecObjectType:
    identifier: str
    long_name: str
    attributes: list[AttributeDefinition] = field(default_factory=list)


@dataclass
class SpecRelationType:
    identifier: str
    long_name: str


@dataclass
class SpecObject:
    identifier: str
    type_ref: Optional[str]              # SPEC-OBJECT-TYPE identifier, may be None
    inferred_from_hierarchy: bool = False


@dataclass
class SpecRelation:
    identifier: str
    source_ref: str
    target_ref: str
    type_ref: Optional[str]


@dataclass
class ReqIFContent:
    spec_object_types: dict[str, SpecObjectType] = field(default_factory=dict)
    spec_relation_types: dict[str, SpecRelationType] = field(default_factory=dict)
    spec_objects: list[SpecObject] = field(default_factory=list)
    spec_relations: list[SpecRelation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Local-name datatype suffix → friendly label (we strip the namespace).
_DATATYPE_SUFFIXES = {
    "DATATYPE-DEFINITION-STRING":      "STRING",
    "DATATYPE-DEFINITION-INTEGER":     "INTEGER",
    "DATATYPE-DEFINITION-REAL":        "REAL",
    "DATATYPE-DEFINITION-BOOLEAN":     "BOOLEAN",
    "DATATYPE-DEFINITION-DATE":        "DATE",
    "DATATYPE-DEFINITION-ENUMERATION": "ENUMERATION",
    "DATATYPE-DEFINITION-XHTML":       "XHTML",
}

# Mirror for attribute-definition elements: the suffix identifies the datatype family.
_ATTR_DEF_SUFFIX_TO_DATATYPE = {
    "ATTRIBUTE-DEFINITION-STRING":      "STRING",
    "ATTRIBUTE-DEFINITION-INTEGER":     "INTEGER",
    "ATTRIBUTE-DEFINITION-REAL":        "REAL",
    "ATTRIBUTE-DEFINITION-BOOLEAN":     "BOOLEAN",
    "ATTRIBUTE-DEFINITION-DATE":        "DATE",
    "ATTRIBUTE-DEFINITION-ENUMERATION": "ENUMERATION",
    "ATTRIBUTE-DEFINITION-XHTML":       "XHTML",
}


def _local(tag: str) -> str:
    """Return the local name of a namespaced tag like '{ns}LOCAL'."""
    return tag.rsplit("}", 1)[-1]


def parse_reqif(path: Path) -> ReqIFContent:
    """Parse a .reqif file and return its content. Never raises on incomplete schemas
    — issues are accumulated in `content.warnings`."""
    content = ReqIFContent()
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XML in {path}: {exc}") from exc
    root = tree.getroot()

    # Build the datatype-id → friendly label map first.
    dt_map: dict[str, str] = {}
    for dt in root.iter():
        suffix = _local(dt.tag)
        if suffix in _DATATYPE_SUFFIXES:
            identifier = dt.get("IDENTIFIER")
            if identifier:
                dt_map[identifier] = _DATATYPE_SUFFIXES[suffix]

    # SPEC-OBJECT-TYPE definitions.
    for sot in root.iter(f"{{{NS['r']}}}SPEC-OBJECT-TYPE"):
        identifier = sot.get("IDENTIFIER")
        if not identifier:
            content.warnings.append("A SPEC-OBJECT-TYPE has no IDENTIFIER; skipped.")
            continue
        long_name = sot.get("LONG-NAME") or ""
        if not long_name:
            content.warnings.append(f"SPEC-OBJECT-TYPE {identifier} has no LONG-NAME.")
        attrs: list[AttributeDefinition] = []
        for child in sot.iter():
            suffix = _local(child.tag)
            datatype = _ATTR_DEF_SUFFIX_TO_DATATYPE.get(suffix)
            if datatype is None:
                continue
            attrs.append(AttributeDefinition(
                identifier=child.get("IDENTIFIER", ""),
                long_name=child.get("LONG-NAME", ""),
                datatype=datatype,
            ))
        content.spec_object_types[identifier] = SpecObjectType(
            identifier=identifier, long_name=long_name, attributes=attrs,
        )

    # SPEC-RELATION-TYPE definitions.
    for srt in root.iter(f"{{{NS['r']}}}SPEC-RELATION-TYPE"):
        identifier = srt.get("IDENTIFIER")
        if not identifier:
            content.warnings.append("A SPEC-RELATION-TYPE has no IDENTIFIER; skipped.")
            continue
        content.spec_relation_types[identifier] = SpecRelationType(
            identifier=identifier, long_name=srt.get("LONG-NAME", ""),
        )

    # SPEC-OBJECTS: harvest type from the <TYPE> child when available.
    for so in root.iter(f"{{{NS['r']}}}SPEC-OBJECT"):
        identifier = so.get("IDENTIFIER")
        if not identifier:
            content.warnings.append("A SPEC-OBJECT has no IDENTIFIER; skipped.")
            continue
        type_ref = _extract_type_ref(so, "SPEC-OBJECT-TYPE-REF")
        content.spec_objects.append(SpecObject(
            identifier=identifier, type_ref=type_ref, inferred_from_hierarchy=False,
        ))

    # SPEC-HIERARCHY fallback: fill missing type_ref for items referenced under a
    # hierarchy that carries the TYPE (DOORS-style indirect typing).
    _resolve_indirect_types(root, content)

    # SPEC-RELATIONS.
    for sr in root.iter(f"{{{NS['r']}}}SPEC-RELATION"):
        identifier = sr.get("IDENTIFIER")
        if not identifier:
            content.warnings.append("A SPEC-RELATION has no IDENTIFIER; skipped.")
            continue
        source = _extract_ref(sr, "SOURCE", "SPEC-OBJECT-REF")
        target = _extract_ref(sr, "TARGET", "SPEC-OBJECT-REF")
        type_ref = _extract_type_ref(sr, "SPEC-RELATION-TYPE-REF")
        content.spec_relations.append(SpecRelation(
            identifier=identifier, source_ref=source or "",
            target_ref=target or "", type_ref=type_ref,
        ))

    # Final warnings on objects whose type stayed unknown.
    untyped = [so.identifier for so in content.spec_objects if so.type_ref is None]
    if untyped:
        content.warnings.append(
            f"{len(untyped)} SPEC-OBJECT(s) have no resolvable type "
            f"(e.g. {untyped[:3]}). Source export may be incomplete."
        )

    return content


def _extract_type_ref(element: ET.Element, ref_local_name: str) -> Optional[str]:
    """Read <TYPE>/<{ref_local_name}>VALUE</…>/</TYPE> from `element`."""
    type_node = element.find(f"r:TYPE", NS)
    if type_node is None:
        return None
    ref = type_node.find(f"r:{ref_local_name}", NS)
    if ref is None or not (ref.text or "").strip():
        return None
    return ref.text.strip()


def _extract_ref(element: ET.Element, parent: str, child: str) -> Optional[str]:
    """Read <{parent}>/<{child}>VALUE</…>/</{parent}> from `element`."""
    parent_node = element.find(f"r:{parent}", NS)
    if parent_node is None:
        return None
    ref = parent_node.find(f"r:{child}", NS)
    if ref is None or not (ref.text or "").strip():
        return None
    return ref.text.strip()


def _resolve_indirect_types(root: ET.Element, content: ReqIFContent) -> None:
    """DOORS-style: the TYPE of an item may be carried by its SpecHierarchy
    wrapper instead of by the SPEC-OBJECT itself. Walk hierarchies and fill
    missing type_refs."""
    by_id = {so.identifier: so for so in content.spec_objects}
    for hierarchy in root.iter(f"{{{NS['r']}}}SPEC-HIERARCHY"):
        hierarchy_type = _extract_type_ref(hierarchy, "SPEC-OBJECT-TYPE-REF")
        if not hierarchy_type:
            continue
        object_ref = hierarchy.find("r:OBJECT/r:SPEC-OBJECT-REF", NS)
        if object_ref is None or not (object_ref.text or "").strip():
            continue
        so_id = object_ref.text.strip()
        so = by_id.get(so_id)
        if so is None or so.type_ref is not None:
            continue
        so.type_ref = hierarchy_type
        so.inferred_from_hierarchy = True
