"""
reporter.py
Output formatters: Rich terminal, JSON, Markdown.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text

from regops.checker import Gap
from regops.loader import ComplianceData
from regops.parser import TraceLink


SEVERITY_STYLE = {
    "critical": ("bold red", "✗"),
    "warning":  ("yellow",   "⚠"),
    "info":     ("dim",      "ℹ"),
}


def report_terminal(
    console: Console,
    repo: Path,
    trace_links: list[TraceLink],
    data: ComplianceData,
    gaps: list[Gap],
) -> None:
    """Print formatted report to terminal using Rich."""

    # Header
    total_reqs = len([r for r in data.requirements.values()
                      if r.type in ("software_requirement", "software_item", "software_unit")])
    covered_reqs = len(set(
        req_id
        for link in trace_links
        for req_id in link.reqs
        if req_id in data.requirements
    ))
    coverage_pct = (covered_reqs / total_reqs * 100) if total_reqs > 0 else 0.0

    console.print()
    console.print("[bold]RegOps Traceability Report[/bold]")
    console.print(f"Repo : [cyan]{repo.resolve()}[/cyan]")
    console.print(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    console.print()

    if not gaps:
        console.print("[bold green]✓ No gaps found. Submission readiness: CLEAR[/bold green]")
        console.print()
        return

    # Gaps table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Sev.", width=10)
    table.add_column("Rule", width=28)
    table.add_column("Message")

    for gap in gaps:
        style, icon = SEVERITY_STYLE.get(gap.severity, ("", "?"))
        table.add_row(
            Text(f"{icon} {gap.severity.upper()}", style=style),
            Text(gap.rule_id, style="dim"),
            gap.message,
        )

    console.print(table)

    # Summary
    critical_count = sum(1 for g in gaps if g.severity == "critical")
    warning_count  = sum(1 for g in gaps if g.severity == "warning")

    console.print(
        f"Coverage : [cyan]{covered_reqs}/{total_reqs}[/cyan] "
        f"SW requirements annotated ({coverage_pct:.0f}%)"
    )
    console.print(
        f"Gaps     : [red]{critical_count} critical[/red]"
        f"  [yellow]{warning_count} warnings[/yellow]"
    )
    console.print()

    if critical_count > 0:
        console.print("[bold red]Submission readiness: BLOCKED[/bold red]")
    else:
        console.print("[bold yellow]Submission readiness: REVIEW NEEDED[/bold yellow]")

    console.print()
    console.print("[dim]Run with --json for machine-readable output.[/dim]")


def report_json(gaps: list[Gap]) -> None:
    """Print gaps as JSON to stdout."""
    payload = [
        {
            "severity": g.severity,
            "rule_id": g.rule_id,
            "node_id": g.node_id,
            "message": g.message,
            "reference": g.reference,
            "details": g.details,
        }
        for g in gaps
    ]
    print(json.dumps({"gaps": payload, "total": len(payload)}, indent=2))


def report_markdown(
    output: Path,
    repo: Path,
    trace_links: list[TraceLink],
    data: ComplianceData,
    gaps: list[Gap],
) -> None:
    """Write a markdown traceability report to file."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# RegOps Traceability Report",
        f"",
        f"**Repo:** `{repo.resolve()}`  ",
        f"**Generated:** {now}  ",
        f"",
        f"---",
        f"",
        f"## Gaps ({len(gaps)} total)",
        f"",
        f"| Severity | Rule | Message | Reference |",
        f"|---|---|---|---|",
    ]

    for gap in gaps:
        icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(gap.severity, "")
        lines.append(
            f"| {icon} {gap.severity.upper()} | `{gap.rule_id}` "
            f"| {gap.message} | {gap.reference} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Coverage",
        f"",
    ]

    total_reqs = len([r for r in data.requirements.values()
                      if r.type in ("software_requirement", "software_item", "software_unit")])
    covered = len(set(
        req_id for link in trace_links
        for req_id in link.reqs
        if req_id in data.requirements
    ))
    lines.append(
        f"- SW requirements annotated: **{covered}/{total_reqs}** "
        f"({covered/total_reqs*100:.0f}%)" if total_reqs > 0
        else "- No SW requirements found."
    )

    critical = sum(1 for g in gaps if g.severity == "critical")
    readiness = "BLOCKED" if critical > 0 else ("REVIEW NEEDED" if gaps else "CLEAR")
    lines += [f"", f"**Submission readiness: {readiness}**", f""]

    output.write_text("\n".join(lines), encoding="utf-8")
