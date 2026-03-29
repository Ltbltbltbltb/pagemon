"""CLI interface for pagemon."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from pagemon.core import PageMon
from pagemon.models import CheckStatus

console = Console()


def _get_engine(db: str | None = None, webhook: str | None = None) -> PageMon:
    from pathlib import Path

    db_path = Path(db) if db else None
    return PageMon(db_path=db_path, webhook_url=webhook)


@click.group()
@click.version_option(package_name="pagemon")
def cli() -> None:
    """pagemon - Monitor web pages for changes from your terminal."""
    pass


@cli.command()
@click.argument("url")
@click.option("--name", "-n", help="Friendly name for this target.")
@click.option("--selector", "-s", help="CSS selector to watch a specific element.")
@click.option("--interval", "-i", default=30, help="Check interval in minutes (default: 30).")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def add(url: str, name: str | None, selector: str | None, interval: int, db: str | None) -> None:
    """Add a URL to monitor."""
    engine = _get_engine(db)
    try:
        target = engine.add(url, name=name, selector=selector, interval=interval)
        console.print(f"[green]Added:[/green] {target.url}")
        if selector:
            console.print(f"  Selector: {selector}")
        console.print(f"  Interval: every {interval}m")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    finally:
        engine.close()


@cli.command("rm")
@click.argument("url")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def remove(url: str, db: str | None) -> None:
    """Remove a URL from monitoring."""
    engine = _get_engine(db)
    try:
        if engine.remove(url):
            console.print(f"[green]Removed:[/green] {url}")
        else:
            console.print(f"[yellow]Not found:[/yellow] {url}")
            sys.exit(1)
    finally:
        engine.close()


@cli.command("ls")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def list_targets(as_json: bool, db: str | None) -> None:
    """List all monitored URLs."""
    engine = _get_engine(db)
    try:
        targets = engine.list_targets()
        if not targets:
            console.print("[dim]No targets configured. Use 'pagemon add <url>' to start.[/dim]")
            return

        if as_json:
            data = [
                {
                    "id": t.id,
                    "url": t.url,
                    "name": t.name,
                    "selector": t.selector,
                    "interval_minutes": t.interval_minutes,
                    "created_at": t.created_at,
                }
                for t in targets
            ]
            click.echo(json.dumps(data, indent=2))
            return

        table = Table(title="Monitored Pages")
        table.add_column("ID", style="dim")
        table.add_column("Name / URL", style="cyan")
        table.add_column("Selector", style="yellow")
        table.add_column("Interval", justify="right")

        for t in targets:
            display = t.name or t.url
            sel = t.selector or "-"
            table.add_row(str(t.id), display, sel, f"{t.interval_minutes}m")

        console.print(table)
    finally:
        engine.close()


@cli.command()
@click.argument("url", required=False)
@click.option("--all", "check_all", is_flag=True, help="Check all targets.")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--webhook", "-w", envvar="PAGEMON_WEBHOOK", help="Webhook URL for notifications.")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def check(
    url: str | None,
    check_all: bool,
    as_json: bool,
    webhook: str | None,
    db: str | None,
) -> None:
    """Check for changes. Use --all or specify a URL."""
    engine = _get_engine(db, webhook)
    try:
        if check_all or url is None:
            results = engine.check_all()
        else:
            target = engine.storage.get_target_by_url(url)
            if not target:
                console.print(f"[red]Not found:[/red] {url}")
                console.print("Use 'pagemon add' first.")
                sys.exit(1)
            results = [engine.check(target)]

        if as_json:
            data = [
                {
                    "url": r.target.url,
                    "name": r.target.name,
                    "status": r.status.value,
                    "error": r.error,
                    "has_diff": r.diff_text is not None,
                    "timestamp": r.timestamp,
                }
                for r in results
            ]
            click.echo(json.dumps(data, indent=2))
            return

        if not results:
            console.print("[dim]No targets to check.[/dim]")
            return

        status_icons = {
            CheckStatus.CHANGED: "[bold red]CHANGED[/bold red]",
            CheckStatus.UNCHANGED: "[green]OK[/green]",
            CheckStatus.ERROR: "[red]ERROR[/red]",
            CheckStatus.NEW: "[blue]NEW[/blue]",
        }

        for r in results:
            name = r.target.name or r.target.url
            icon = status_icons.get(r.status, r.status.value)
            console.print(f"  {icon}  {name}")
            if r.error:
                console.print(f"         [dim]{r.error}[/dim]")
            if r.diff_text and r.status == CheckStatus.CHANGED:
                _print_diff(r.diff_text)
    finally:
        engine.close()


@cli.command()
@click.argument("url")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def diff(url: str, db: str | None) -> None:
    """Show the latest diff for a URL."""
    engine = _get_engine(db)
    try:
        diff_text = engine.get_diff(url)
        if diff_text is None:
            console.print("[dim]No diff available (need at least 2 snapshots).[/dim]")
            return
        _print_diff(diff_text)
    finally:
        engine.close()


@cli.command()
@click.argument("url")
@click.option("--limit", "-l", default=10, help="Number of snapshots to show.")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def history(url: str, limit: int, db: str | None) -> None:
    """Show snapshot history for a URL."""
    engine = _get_engine(db)
    try:
        snapshots = engine.get_history(url, limit=limit)
        if not snapshots:
            console.print("[dim]No history found.[/dim]")
            return

        table = Table(title=f"History: {url}")
        table.add_column("ID", style="dim")
        table.add_column("Timestamp")
        table.add_column("Hash", style="cyan")
        table.add_column("Status", justify="right")
        table.add_column("Size", justify="right")

        for s in snapshots:
            table.add_row(
                str(s.id),
                s.timestamp[:19],
                s.content_hash[:12],
                str(s.status_code),
                f"{len(s.content):,}",
            )

        console.print(table)
    finally:
        engine.close()


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["json", "csv"]), default="json")
@click.option("--db", envvar="PAGEMON_DB", hidden=True)
def export(fmt: str, db: str | None) -> None:
    """Export all targets and latest snapshots."""
    engine = _get_engine(db)
    try:
        targets = engine.list_targets()
        data = []
        for t in targets:
            snap = engine.storage.get_latest_snapshot(t.id)
            entry = {
                "url": t.url,
                "name": t.name,
                "selector": t.selector,
                "interval_minutes": t.interval_minutes,
                "last_check": snap.timestamp if snap else None,
                "last_hash": snap.content_hash[:12] if snap else None,
            }
            data.append(entry)

        if fmt == "json":
            click.echo(json.dumps(data, indent=2))
        elif fmt == "csv":
            if data:
                click.echo(",".join(data[0].keys()))
                for row in data:
                    click.echo(",".join(str(v) for v in row.values()))
    finally:
        engine.close()


def _print_diff(diff_text: str) -> None:
    """Pretty-print a unified diff."""
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(f"[dim]{line}[/dim]")
