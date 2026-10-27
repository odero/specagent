"""
SpecAgent — CLI Entry Point

Usage:
  specagent run "Build a REST API for a todo app"          # inline ask
  specagent run --file feature.txt --hitm false            # from file, autonomous
  specagent dashboard                                      # launch dashboard only
  specagent config                                         # show resolved config
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

app = typer.Typer(
    name="specagent",
    help="Autonomous spec-driven software development agent",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


def _banner() -> None:
    console.print(Panel.fit(
        "[bold blue]SpecAgent[/bold blue] [dim]— Autonomous Dev Pipeline[/dim]\n"
        "[dim]Powered by Microsoft Semantic Kernel · SpecKit · GitHub Copilot[/dim]",
        border_style="blue",
    ))


# ─────────────────────────────────────────────────────────────────────────────
# `run` command
# ─────────────────────────────────────────────────────────────────────────────
@app.command()
def run(
    ask: str = typer.Argument(
        ...,
        help="Feature/scenario description (quote it). Use '-' to read from stdin.",
    ),
    title: str = typer.Option(
        "",
        "--title", "-t",
        help="Short title for the task (auto-generated if omitted)",
    ),
    file: Path = typer.Option(
        None,
        "--file", "-f",
        help="Read the feature description from a file instead",
    ),
    hitm: bool = typer.Option(
        None,
        "--hitm/--no-hitm",
        help="Human-in-the-loop mode (overrides .env setting)",
    ),
    dashboard: bool = typer.Option(
        True,
        "--dashboard/--no-dashboard",
        help="Launch the dashboard alongside the pipeline",
    ),
    host: str = typer.Option("localhost", "--host", help="Dashboard host"),
    port: int = typer.Option(8000, "--port", "-p", help="Dashboard port"),
) -> None:
    """Start a new autonomous development pipeline from a feature ask."""
    _banner()

    # Resolve description
    if file:
        description = file.read_text(encoding="utf-8").strip()
    elif ask == "-":
        description = sys.stdin.read().strip()
    else:
        description = ask.strip()

    if not description:
        console.print("[red]Error:[/red] Feature description cannot be empty.")
        raise typer.Exit(1)

    task_title = title or description[:60].replace("\n", " ")

    from config import settings
    effective_hitm = hitm if hitm is not None else settings.hitm_mode

    console.print(f"\n[bold]Task:[/bold] {task_title}")
    console.print(f"[bold]Mode:[/bold] {'[yellow]HITM (Human-in-the-Loop)[/yellow]' if effective_hitm else '[green]Fully Autonomous[/green]'}")
    console.print(f"[bold]LLM:[/bold]  {settings.llm_provider.value} / {settings.effective_model}\n")

    if dashboard:
        console.print(f"[dim]Dashboard → http://{host}:{port}[/dim]\n")

    asyncio.run(_run_pipeline(task_title, description, effective_hitm, dashboard, host, port))


async def _run_pipeline(
    title: str,
    description: str,
    hitm: bool,
    with_dashboard: bool,
    host: str,
    port: int,
) -> None:
    from orchestrator import Coordinator
    from dashboard import create_app

    tasks = []

    if with_dashboard:
        fastapi_app = create_app()
        config = uvicorn.Config(fastapi_app, host=host, port=port, log_level="error")
        server = uvicorn.Server(config)
        tasks.append(asyncio.create_task(server.serve()))

    coordinator = Coordinator()
    pipeline = asyncio.create_task(coordinator.run(title, description, hitm))
    tasks.append(pipeline)

    try:
        await pipeline   # wait for pipeline to finish
        # Give server a moment to serve last state updates
        await asyncio.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        for t in tasks:
            t.cancel()

    console.print("\n[bold green]✅ Pipeline complete![/bold green]")
    console.print(f"[dim]Deliverables saved to ./output/[/dim]")


# ─────────────────────────────────────────────────────────────────────────────
# `dashboard` command (dashboard only, no pipeline)
# ─────────────────────────────────────────────────────────────────────────────
@app.command()
def dashboard(
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
) -> None:
    """Launch the SpecAgent dashboard without starting a pipeline."""
    _banner()
    console.print(f"\n[bold]Dashboard[/bold] → http://{host}:{port}\n")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    from dashboard import create_app
    fastapi_app = create_app()
    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


# ─────────────────────────────────────────────────────────────────────────────
# `config` command
# ─────────────────────────────────────────────────────────────────────────────
@app.command()
def config() -> None:
    """Show the resolved configuration."""
    _banner()

    from config import settings

    table = Table(title="SpecAgent Configuration", show_header=True, header_style="bold blue")
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    rows = [
        ("LLM Provider",      settings.llm_provider.value),
        ("Model",             settings.effective_model),
        ("API Key set",       "✓" if settings.effective_api_key else "✗ MISSING"),
        ("HITM Mode",         str(settings.hitm_mode)),
        ("Max Agents",        str(settings.max_concurrent_agents)),
        ("Agent Timeout (s)", str(settings.agent_timeout_seconds)),
        ("Dashboard Port",    str(settings.dashboard_port)),
        ("Output Dir",        str(settings.output_dir)),
        ("Specs Dir",         str(settings.specs_dir)),
    ]
    for k, v in rows:
        warning = "[red]" if "MISSING" in v else ""
        table.add_row(k, f"{warning}{v}{'[/red]' if warning else ''}")

    console.print(table)

    if not settings.effective_api_key:
        console.print("\n[red]⚠  No API key found.[/red] Copy [bold].env.example[/bold] to [bold].env[/bold] and add your key.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app()
