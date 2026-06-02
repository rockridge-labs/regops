"""
base.py
Abstract contract for compliance-source importers.

An importer translates the data of an external compliance tool
(MatrixReq, Greenlight Guru, TraceX, a ReqIF export, …) into the
RegOps YAML structure under `compliance/`. Each concrete importer
lives in its own module (e.g. regops/importers/reqif.py) and is
registered via the @register decorator from regops.importers.

Lifecycle on a `regops import` invocation:

    1. discover()  — optional, returns a dict of source metadata
                     (project name, version, object counts) without
                     pulling the full payload. Lets the CLI display
                     a confirmation before a long fetch.
    2. fetch()     — pulls every object and returns a normalised
                     ImportPayload (RegOps-shaped dicts).
    3. to_compliance_yaml(payload, target)
                   — writes the payload as YAML files under target.
                     Default implementation in this base class
                     handles the standard RegOps layout, so most
                     importers only override discover() and fetch().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ImportPayload:
    """Normalised, RegOps-shaped objects ready to be written to YAML.

    Each item in `requirements` / `risks` / `tests` is a dict whose
    keys match the RegOps YAML schema (id, type, title, …). Importers
    are responsible for the source-format → RegOps-format translation;
    this dataclass is the agreed-upon hand-off shape.
    """
    requirements: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    tests: list[dict] = field(default_factory=list)
    source_name: str = ""
    source_metadata: dict = field(default_factory=dict)


class ImporterBase(ABC):
    """Subclass and decorate with @register to plug a new source."""

    # Registry key. Lowercase, kebab-case. Used in `regops import --from <name>`.
    name: str = ""

    def discover(self, **kwargs) -> dict:
        """Connect and return lightweight metadata. Default: empty."""
        return {}

    @abstractmethod
    def fetch(self, **kwargs) -> ImportPayload:
        """Pull every object from the source and normalise to RegOps shape."""

    def to_compliance_yaml(
        self,
        payload: ImportPayload,
        target: Path,
    ) -> list[Path]:
        """Write payload to target/compliance/{requirements,risks,tests}/.
        Returns the list of files written, in stable order.
        Importers can override for custom layouts but the default fits 99% of cases."""

        written: list[Path] = []
        bucket_map = [
            ("requirements", payload.requirements),
            ("risks",        payload.risks),
            ("tests",        payload.tests),
        ]
        for bucket, items in bucket_map:
            if not items:
                continue
            bucket_dir = target / "compliance" / bucket
            bucket_dir.mkdir(parents=True, exist_ok=True)
            for item in items:
                if "id" not in item:
                    continue  # silently skip malformed entries — importer's job to validate
                path = bucket_dir / f"{item['id']}.yaml"
                path.write_text(
                    yaml.safe_dump(item, sort_keys=False, allow_unicode=True),
                    encoding="utf-8",
                )
                written.append(path)
        return written
