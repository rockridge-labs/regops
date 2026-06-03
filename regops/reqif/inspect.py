"""
inspect.py
Renders the human report and the empty mapping skeleton.

Exit codes (returned by run_inspect):
  0 — success
  1 — parse error (malformed XML, file unreadable, …)
  2 — unsupported format (.reqifz)
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

from regops.reqif.parser import ReqIFContent, parse_reqif


REQIFZ_REJECT_MSG = (
    "Error: .reqifz (zipped ReqIF) is not yet supported.\n"
    "The current `regops reqif inspect` only handles raw .reqif XML.\n"
    "Tracking: issue #6 phase ultérieure."
)


def run_inspect(
    console: Console,
    path: Path,
    output_skeleton: Optional[Path] = None,
) -> int:
    """Inspect `path`. Print the report to `console`; either print the
    skeleton inline (default) or write it to `output_skeleton`."""

    if path.suffix.lower() == ".reqifz":
        console.print(f"[red]{REQIFZ_REJECT_MSG}[/red]")
        return 2

    try:
        content = parse_reqif(path)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Error parsing {path}: {exc}[/red]")
        return 1

    _render_report(console, content, path)

    skeleton = _render_skeleton(content, path)
    if output_skeleton is not None:
        output_skeleton.write_text(skeleton, encoding="utf-8")
        console.print(f"[green]Skeleton written to {output_skeleton}[/green]")
    else:
        console.print()
        console.print(skeleton)
    return 0


def _render_report(console: Console, content: ReqIFContent, source: Path) -> None:
    """Print the human-readable enumeration."""

    console.print()
    console.print(f"[bold]ReqIF Inspection — {source.name}[/bold]")
    console.print()

    type_counts = Counter(so.type_ref for so in content.spec_objects if so.type_ref)
    inferred_counts = Counter(
        so.type_ref for so in content.spec_objects
        if so.inferred_from_hierarchy and so.type_ref
    )

    # SPEC-OBJECT-TYPEs and their attributes.
    sot_table = Table(title="SPEC-OBJECT-TYPE", box=box.SIMPLE, show_header=True)
    sot_table.add_column("ID")
    sot_table.add_column("Long name")
    sot_table.add_column("Objects", justify="right")
    sot_table.add_column("Attributes")
    for sot in content.spec_object_types.values():
        attr_str = ", ".join(f"{a.long_name or a.identifier} ({a.datatype})"
                             for a in sot.attributes) or "-"
        count = type_counts.get(sot.identifier, 0)
        inf = inferred_counts.get(sot.identifier, 0)
        count_str = f"{count}" + (f" ({inf} inferred)" if inf else "")
        sot_table.add_row(sot.identifier, sot.long_name or "-", count_str, attr_str)
    console.print(sot_table)

    # SPEC-RELATIONS.
    rel_counts = Counter(sr.type_ref for sr in content.spec_relations if sr.type_ref)
    rel_table = Table(title="SPEC-RELATION", box=box.SIMPLE, show_header=True)
    rel_table.add_column("Relation type ID")
    rel_table.add_column("Long name")
    rel_table.add_column("Count", justify="right")
    for srt_id, srt in content.spec_relation_types.items():
        rel_table.add_row(srt_id, srt.long_name or "-", str(rel_counts.get(srt_id, 0)))
    if rel_counts:
        console.print(rel_table)
    else:
        console.print("[dim]No SPEC-RELATIONS detected.[/dim]")

    # Warnings raised during parsing.
    if content.warnings:
        console.print()
        console.print("[yellow]Warnings:[/yellow]")
        for w in content.warnings:
            console.print(f"  [yellow]⚠[/yellow] {w}")


def _render_skeleton(content: ReqIFContent, source: Path) -> str:
    """Emit a YAML import_mapping skeleton with empty values."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    type_counts = Counter(so.type_ref for so in content.spec_objects if so.type_ref)
    rel_counts = Counter(sr.type_ref for sr in content.spec_relations if sr.type_ref)

    out: list[str] = [
        f"# regops reqif inspect generated this on {now}",
        f"# Source: {source.name}",
        f"# Spec-objects: {len(content.spec_objects)}  "
        f"Spec-relations: {len(content.spec_relations)}",
        "#",
        "# ⚠️ WARNING — every mapping value below is intentionally empty.",
        "# You MUST fill them manually. An incorrect mapping silently corrupts",
        '# compliance traceability. See CLAUDE.md "Ne pas inventer des règles".',
        "",
        "import_mapping:",
        "  reqif:",
        "    spec_object_types:",
    ]
    for sot in content.spec_object_types.values():
        count = type_counts.get(sot.identifier, 0)
        out.append(
            f"      # {sot.identifier} — \"{sot.long_name}\" — "
            f"{count} object{'s' if count != 1 else ''}"
        )
        # Use the long_name as the key when available, fall back to identifier.
        key = sot.long_name or sot.identifier
        out.append(f"      \"{key}\": \"\"")
    out.append("    spec_relation_types:")
    if not content.spec_relation_types:
        out.append("      {}  # no SPEC-RELATION-TYPE present in this file")
    else:
        for srt in content.spec_relation_types.values():
            count = rel_counts.get(srt.identifier, 0)
            out.append(
                f"      # {srt.identifier} — \"{srt.long_name}\" — "
                f"{count} occurrence{'s' if count != 1 else ''}"
            )
            key = srt.long_name or srt.identifier
            out.append(f"      \"{key}\": \"\"")
    out.append("")
    return "\n".join(out)
