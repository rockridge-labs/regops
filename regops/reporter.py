"""
reporter.py
Output formatters: Rich terminal, JSON, Markdown.
"""

import json
import subprocess
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
from regops.schema import default_schema


def _sw_req_types(data: ComplianceData) -> set[str]:
    """Resolve which node-type names map to the SW requirement concepts."""
    schema = data.schema if data.schema.node_types else default_schema()
    out: set[str] = set()
    for concept in ("software_requirement", "software_item", "software_unit"):
        out |= schema.types_with_maps_to(concept)
    return out


def _git_short_sha(repo: Path) -> Optional[str]:
    """Return short SHA of HEAD in `repo` if available, else None.
    Fails silently when git is missing, repo is not a git tree, or it has no commits yet."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo, capture_output=True, text=True, timeout=2, check=False,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            return sha or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _coverage(data: ComplianceData, trace_links: list[TraceLink]) -> tuple[int, int, float]:
    """(covered_reqs, total_sw_reqs, pct) — used in both terminal and markdown outputs."""
    sw_types = _sw_req_types(data)
    total = len([r for r in data.requirements.values() if r.type in sw_types])
    covered = len(set(
        req_id for link in trace_links
        for req_id in link.reqs
        if req_id in data.requirements
    ))
    pct = (covered / total * 100) if total > 0 else 0.0
    return covered, total, pct


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

    covered_reqs, total_reqs, coverage_pct = _coverage(data, trace_links)
    sha = _git_short_sha(repo)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    console.print()
    console.print("[bold]RegOps Traceability Report[/bold]")
    header = f"Repo : [cyan]{repo.resolve()}[/cyan]"
    if sha:
        header += f"  |  Commit : [cyan]{sha}[/cyan]"
    header += f"  |  {now_str}"
    console.print(header)
    console.print()

    if not gaps:
        info_style, info_icon = SEVERITY_STYLE["info"]
        console.print(
            Text(
                f"{info_icon} INFO   {covered_reqs} / {total_reqs} SW requirements covered "
                f"({coverage_pct:.0f}%)",
                style=info_style,
            )
        )
        console.print()
        console.print("[bold green]✓ No gaps found. Submission readiness: CLEAR[/bold green]")
        console.print()
        return

    # Gaps table — coverage info appended as the final row.
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

    info_style, info_icon = SEVERITY_STYLE["info"]
    table.add_row(
        Text(f"{info_icon} INFO", style=info_style),
        Text("", style="dim"),
        Text(
            f"{covered_reqs} / {total_reqs} SW requirements covered ({coverage_pct:.0f}%)",
            style=info_style,
        ),
    )

    console.print(table)

    # Summary
    critical_count = sum(1 for g in gaps if g.severity == "critical")
    warning_count  = sum(1 for g in gaps if g.severity == "warning")

    console.print(
        f"Gaps : [red]{critical_count} critical[/red]"
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
    sha = _git_short_sha(repo)
    covered, total_reqs, coverage_pct = _coverage(data, trace_links)

    lines = [
        f"# RegOps Traceability Report",
        f"",
        f"**Repo:** `{repo.resolve()}`  ",
    ]
    if sha:
        lines.append(f"**Commit:** `{sha}`  ")
    lines += [
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

    # Append coverage as an INFO row inside the gaps table.
    if total_reqs > 0:
        lines.append(
            f"| 🔵 INFO |  | {covered} / {total_reqs} SW requirements covered "
            f"({coverage_pct:.0f}%) | Coverage |"
        )

    critical = sum(1 for g in gaps if g.severity == "critical")
    readiness = "BLOCKED" if critical > 0 else ("REVIEW NEEDED" if gaps else "CLEAR")
    lines += [f"", f"**Submission readiness: {readiness}**", f""]

    output.write_text("\n".join(lines), encoding="utf-8")
