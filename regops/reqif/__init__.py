"""regops.reqif — read-only ReqIF tooling.

Phase 1 ships `inspect` only — parses a .reqif file, enumerates every
SPEC-OBJECT-TYPE / attribute / SPEC-RELATION it actually contains, and
emits an empty mapping skeleton the user fills manually. No automatic
mapping, no compliance/ writes, no .reqifz support.

The principle, codified in the task brief 2026-06-02 and enforced by
CLAUDE.md (do not invent rules): ReqIF carries no semantic standard,
so guessing a mapping silently corrupts the trace.

A future phase will add `regops reqif import` which consumes the
human-validated mapping to produce compliance/ YAML files.
"""

from regops.reqif.parser import (
    AttributeDefinition,
    ReqIFContent,
    SpecObject,
    SpecObjectType,
    SpecRelation,
    SpecRelationType,
    parse_reqif,
)
from regops.reqif.inspect import run_inspect

__all__ = [
    "AttributeDefinition",
    "ReqIFContent",
    "SpecObject",
    "SpecObjectType",
    "SpecRelation",
    "SpecRelationType",
    "parse_reqif",
    "run_inspect",
]
