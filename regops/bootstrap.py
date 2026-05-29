"""
bootstrap.py
Materialize a fresh compliance/ + .regops/ skeleton from packaged YAML
templates. Used by `regops init`.

Templates live in regops/templates/*.yaml and are shipped with the wheel
via the [tool.hatch.build.targets.wheel.force-include] entry in
pyproject.toml. Each template is parameter-substituted with {{STANDARD}}
and {{SAFETY_CLASS}} before being written to the target repo.
"""

from importlib.resources import files
from pathlib import Path

# Mapping: template filename (in regops/templates/) → target path relative to repo root.
TEMPLATE_TARGETS: dict[str, str] = {
    "schema.yaml":   ".regops/schema.yaml",
    "UN-001.yaml":   "compliance/requirements/UN-001.yaml",
    "SYS-001.yaml":  "compliance/requirements/SYS-001.yaml",
    "SR-001.yaml":   "compliance/requirements/SR-001.yaml",
    "RISK-001.yaml": "compliance/risks/RISK-001.yaml",
    "TC-001.yaml":   "compliance/tests/TC-001.yaml",
}

# CLI standard slug → schema active_standards string.
_STANDARD_SLUGS: dict[str, str] = {
    "iec62304": "iec_62304",
    "iso14971": "iso_14971",
    "iso13485": "iso_13485",
}


def bootstrap_repo(
    repo: Path,
    standard: str = "iec62304",
    safety_class: str = "B",
    force: bool = False,
) -> list[Path]:
    """Create compliance + schema skeleton in `repo`. Returns list of files written.
    Raises FileExistsError on the first target that already exists, unless force=True."""

    created: list[Path] = []
    templates = files("regops.templates")

    for tpl_name, target_rel in TEMPLATE_TARGETS.items():
        target = repo / target_rel

        if target.exists() and not force:
            raise FileExistsError(str(target))

        raw = (templates / tpl_name).read_text(encoding="utf-8")
        rendered = _render(raw, standard, safety_class)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        created.append(target)

    return created


def _render(content: str, standard: str, safety_class: str) -> str:
    """Apply placeholder substitution. Unknown standards pass through verbatim."""
    std_id = _STANDARD_SLUGS.get(standard.lower(), standard)
    return (content
            .replace("{{STANDARD}}", std_id)
            .replace("{{SAFETY_CLASS}}", safety_class.upper()))
