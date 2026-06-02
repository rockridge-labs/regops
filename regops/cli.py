"""RegOps CLI — entrypoint Typer."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

app = typer.Typer(
    name="regops",
    help="Compliance as Code — traceability for medical device software.",
    add_completion=False,
)
console = Console()


@app.command()
def check(
    repo: Path = typer.Option(
        Path("."),
        "--repo", "-r",
        help="Path to the repository to analyse.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output gaps as JSON (for CI/CD integration).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Export report to markdown file.",
    ),
) -> None:
    """Analyse a repository and report compliance gaps."""
    from regops.parser import parse_repo
    from regops.loader import load_compliance
    from regops.checker import check_traceability
    from regops.reporter import report_terminal, report_json, report_markdown

    console.print(f"[bold]RegOps[/bold] — scanning [cyan]{repo.resolve()}[/cyan]")

    trace_links = parse_repo(repo)
    compliance_data = load_compliance(repo)
    gaps = check_traceability(compliance_data, trace_links)

    if json_output:
        report_json(gaps)
    else:
        report_terminal(console, repo, trace_links, compliance_data, gaps)

    if output:
        report_markdown(output, repo, trace_links, compliance_data, gaps)
        console.print(f"[green]Report saved to {output}[/green]")

    # Exit code non-zero if critical gaps
    critical = [g for g in gaps if g.severity == "critical"]
    if critical:
        raise typer.Exit(code=1)


@app.command()
def init(
    repo: Path = typer.Option(
        Path("."),
        "--repo", "-r",
        help="Path to the repository to initialise.",
    ),
    standard: str = typer.Option(
        "iec62304",
        "--standard",
        help="Regulatory standard (iec62304, iso14971, iso13485).",
    ),
    safety_class: str = typer.Option(
        "B",
        "--class",
        help="Software safety class (A, B, C).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing files in target repo.",
    ),
) -> None:
    """Bootstrap compliance structure in a repository."""
    from regops.bootstrap import bootstrap_repo

    console.print(f"[bold]RegOps init[/bold] — {repo.resolve()}")

    try:
        created = bootstrap_repo(repo, standard, safety_class, force)
    except FileExistsError as e:
        console.print(
            f"[red]Aborting — {e} already exists. "
            f"Re-run with [bold]--force[/bold] to overwrite.[/red]"
        )
        raise typer.Exit(code=1)

    for path in created:
        console.print(f"  [green]+[/green] {path.relative_to(repo)}")

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Edit [cyan].regops/schema.yaml[/cyan] to match your taxonomy.")
    console.print("  2. Replace example files in [cyan]compliance/[/cyan] with your real artefacts.")
    console.print("  3. Run [cyan]regops check[/cyan] to validate.")


@app.command("import")
def import_(
    from_: str = typer.Option(
        ...,
        "--from",
        help="Importer name (see `regops import --list` for the registered importers).",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output", "-o",
        help="Target repo root (compliance/ subtree is created beneath it).",
    ),
    list_: bool = typer.Option(
        False,
        "--list",
        help="List registered importers and exit.",
    ),
) -> None:
    """Import compliance data from an external tool into this repo."""
    from regops.importers import get_importer, list_importers

    if list_:
        names = list_importers()
        if not names:
            console.print("[dim]No importers registered.[/dim]")
        else:
            console.print("[bold]Available importers:[/bold]")
            for n in names:
                console.print(f"  • {n}")
        return

    try:
        cls = get_importer(from_)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    importer = cls()
    console.print(f"[bold]RegOps import[/bold] — source: [cyan]{importer.name}[/cyan]")
    payload = importer.fetch()
    written = importer.to_compliance_yaml(payload, output)
    for path in written:
        console.print(f"  [green]+[/green] {path.relative_to(output)}")
    console.print()
    console.print(
        f"[bold]Imported {len(written)} files[/bold] "
        f"({len(payload.requirements)} reqs, {len(payload.risks)} risks, "
        f"{len(payload.tests)} tests). Run [cyan]regops check[/cyan] to validate."
    )


@app.command()
def report(
    repo: Path = typer.Option(Path("."), "--repo", "-r"),
    output: Path = typer.Option(
        Path("traceability-report.md"),
        "--output", "-o",
        help="Output markdown file path.",
    ),
) -> None:
    """Generate a markdown traceability report."""
    from regops.parser import parse_repo
    from regops.loader import load_compliance
    from regops.checker import check_traceability
    from regops.reporter import report_markdown

    trace_links = parse_repo(repo)
    compliance_data = load_compliance(repo)
    gaps = check_traceability(compliance_data, trace_links)
    report_markdown(output, repo, trace_links, compliance_data, gaps)
    console.print(f"[green]Report saved to {output}[/green]")


if __name__ == "__main__":
    app()
