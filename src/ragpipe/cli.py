from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ragpipe import __version__
from ragpipe.config import load_pipeline
from ragpipe.highlevel import ingest, query

app = typer.Typer(
    name="ragpipe",
    help="Declarative RAG pipeline. Ingest any data source into vector databases.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

BANNER = f"[bold cyan]RAGPipe[/bold cyan] [dim]v{__version__}[/dim]"


def _print_banner():
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]RAGPipe[/bold cyan] [dim]v{__version__}[/dim]\n"
            "[dim]Sources → Transforms → Sinks[/dim]",
            border_style="cyan",
        )
    )
    console.print()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _print_banner()
        console.print("  [bold]ingest[/bold]    Ingest data from any source\n")
        console.print("  [bold]query[/bold]     Search your ingested data\n")
        console.print("  [bold]run[/bold]       Execute a pipeline YAML config\n")
        console.print("  [bold]init[/bold]      Create a starter pipeline.yaml\n")
        console.print()


@app.command()
def init(
    output: str = typer.Option("pipeline.yaml", "--output", "-o", help="Output file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if exists"),
):
    _print_banner()

    out_path = Path(output)
    if out_path.exists() and not force:
        console.print(f"[red]✗[/red] {output} already exists. Use --force to overwrite.")
        raise typer.Exit(1)

    template = """# RAGPipe Pipeline Configuration
# Docs: https://github.com/avasis-ai/ragpipe

source:
  type: file          # file | git | web
  paths:
    - ./docs          # Local directory or file paths

transforms:
  - type: html_cleaner
  - type: recursive_chunker
    chunk_size: 512
    chunk_overlap: 64
  - type: auto_embed   # Auto-detects: Ollama > OpenAI > sentence-transformers

sinks:
  - type: json
    output_path: ./ragpipe_output.json
    include_embeddings: true
"""
    out_path.write_text(template)
    console.print(f"[green]✓[/green] Created [bold]{output}[/bold]")
    console.print(f"[dim]  Edit the config, then run: ragpipe run {output}[/dim]")


@app.command()
def run(
    config_path: Path = typer.Argument(..., help="Path to pipeline.yaml"),
):
    _print_banner()

    if not config_path.exists():
        console.print(f"[red]✗[/red] Pipeline config not found: {config_path}")
        raise typer.Exit(1)

    console.print(f"[dim]Loading {config_path}...[/dim]")

    try:
        pipeline = load_pipeline(config_path)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load pipeline: {e}")
        raise typer.Exit(1)

    console.print("[bold]Running pipeline...[/bold]\n")

    start = time.time()
    try:
        stats = pipeline.run()
    except Exception as e:
        console.print(f"[red]✗[/red] Pipeline failed: {e}")
        raise typer.Exit(1)

    elapsed = time.time() - start

    table = Table(title="Pipeline Results", border_style="cyan", show_header=False)
    table.add_column("Metric", style="dim", width=16)
    table.add_column("Value", style="bold green")
    table.add_row("Extracted", str(stats["extracted"]))
    table.add_row("Transformed", str(stats["transformed"]))
    table.add_row("Written", str(stats["written"]))
    table.add_row("Time", f"{elapsed:.2f}s")
    console.print(table)


@app.command("ingest")
def ingest_cmd(
    source: str = typer.Argument(..., help="File path, git URL, or web URL"),
    sink: str = typer.Option("json", "--sink", "-s", help="Target sink: json, qdrant, pinecone"),
    sink_path: str = typer.Option(
        "./ragpipe_output.json", "--sink-path", help="Output path for JSON sink"
    ),
    chunk_size: int = typer.Option(512, "--chunk-size", "-c", help="Chunk size in characters"),
    chunk_overlap: int = typer.Option(64, "--overlap", help="Chunk overlap in characters"),
    embed: bool = typer.Option(False, "--embed", "-e", help="Generate embeddings"),
    collection: str = typer.Option("ragpipe", "--collection", help="Vector DB collection name"),
    clean: bool = typer.Option(True, "--clean/--no-clean", help="Clean HTML"),
    pii: bool = typer.Option(False, "--pii", help="Remove PII"),
):
    _print_banner()
    console.print(f"[dim]Source:[/dim] {source}")
    console.print(f"[dim]Sink:[/dim]   {sink}")
    if embed:
        console.print("[dim]Embeddings: auto-detect[/dim]")
    console.print()

    start = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Ingesting...[/cyan]", total=None)

        try:
            stats = ingest(
                source=source,
                sink=sink,
                sink_path=sink_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                embed=embed,
                collection=collection,
                clean_html=clean,
                remove_pii=pii,
            )
        except Exception as e:
            progress.stop()
            console.print(f"\n[red]✗[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, total=1, completed=1)

    elapsed = time.time() - start

    table = Table(title="Ingestion Complete", border_style="green", show_header=False)
    table.add_column("Metric", style="dim", width=16)
    table.add_column("Value", style="bold green")
    table.add_row("Extracted", str(stats["extracted"]))
    table.add_row("Chunks", str(stats["transformed"]))
    table.add_row("Written", str(stats["written"]))
    table.add_row("Time", f"{elapsed:.2f}s")
    console.print(table)


@app.command("query")
def query_cmd(
    text: str = typer.Argument(..., help="Search query"),
    sink: str = typer.Option("json", "--sink", "-s", help="Data sink to query"),
    sink_path: str = typer.Option(
        "./ragpipe_output.json", "--sink-path", help="Path for JSON sink"
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
    collection: str = typer.Option("ragpipe", "--collection", help="Vector DB collection"),
):
    _print_banner()

    with console.status("[bold cyan]Searching..."):
        try:
            results = query(
                text=text,
                sink=sink,
                sink_path=sink_path,
                top_k=top_k,
                collection=collection,
            )
        except Exception as e:
            console.print(f"\n[red]✗[/red] {e}")
            raise typer.Exit(1)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(
        title=f'Results for: [magenta]"{text}"[/magenta]',
        show_lines=True,
        border_style="cyan",
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Score", justify="right", style="green", width=8)
    table.add_column("Content", style="white", max_width=80, no_wrap=False)
    table.add_column("Source", style="cyan", max_width=30)

    for i, doc in enumerate(results, 1):
        score = doc.metadata.get("score", 0)
        source = doc.metadata.get("path", doc.metadata.get("url", doc.metadata.get("source", "")))
        preview = doc.content[:200].replace("\n", " ")
        table.add_row(str(i), f"{score:.3f}", preview, source)

    console.print(table)
    console.print(f"\n[dim]Showing {len(results)} of {len(results)} results[/dim]")
