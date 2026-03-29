from __future__ import annotations

import json
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
    help="RAG pipeline for any system. Ingest, index, search, and serve.",
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


def _results_table(text: str, results):
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
    console.print(f"\n[dim]Showing {len(results)} results[/dim]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _print_banner()
        console.print("  [bold]Core[/bold]")
        console.print("    ingest      Ingest data from any source")
        console.print("    query       Search your ingested data")
        console.print("    index       Smart-index a codebase")
        console.print("    run         Execute a pipeline YAML")
        console.print("    init        Create a starter pipeline.yaml")
        console.print()
        console.print("  [bold]Integrations[/bold]")
        console.print("    watch       Watch directory and auto-reindex")
        console.print("    serve       Start local API server")
        console.print("    search      Search with fzf integration")
        console.print("    git         Install git hooks for auto-indexing")
        console.print("    vscode      Generate VSCode tasks and settings")
        console.print("    macos       macOS Spotlight integration")
        console.print("    linux       systemd service generation")
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
    mode: str = typer.Option("auto", "--mode", help="Search mode: auto, semantic, keyword"),
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
                mode=mode,
            )
        except Exception as e:
            console.print(f"\n[red]✗[/red] {e}")
            raise typer.Exit(1)
    _results_table(text, results)


# ─── INDEX ────────────────────────────────────────────────────────────────────


@app.command()
def index(
    path: str = typer.Argument(".", help="Project directory to index"),
    sink_path: str = typer.Option("./ragpipe_output.json", "--sink-path", help="Output path"),
    chunk_size: int = typer.Option(512, "--chunk-size", "-c", help="Chunk size"),
    chunk_overlap: int = typer.Option(64, "--overlap", help="Chunk overlap"),
    embed: bool = typer.Option(False, "--embed", "-e", help="Generate embeddings"),
    exclude: list[str] = typer.Option([], "--exclude", "-x", help="Extra ignore patterns"),
    max_file_size: int = typer.Option(100_000, "--max-file-size", help="Max file size in bytes"),
):
    _print_banner()
    from ragpipe.integrations.indexer import detect_project_type, index_project
    from ragpipe.transforms import RecursiveChunker, AutoEmbed
    from ragpipe.sinks import JSONSink

    project_type = detect_project_type(path)
    console.print(f"[dim]Project:[/dim] {path} [dim](type: {project_type})[/dim]")
    console.print(f"[dim]Output:[/dim]  {sink_path}")
    console.print()

    start = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning project...[/cyan]", total=None)
        try:
            docs = index_project(path, ignore_extra=exclude or None, max_file_size=max_file_size)
        except Exception as e:
            progress.stop()
            console.print(f"\n[red]✗[/red] {e}")
            raise typer.Exit(1)
        progress.update(task, description=f"[cyan]Found {len(docs)} files, chunking...[/cyan]")

        transforms = [RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)]
        if embed:
            transforms.append(AutoEmbed())

        all_chunks = []
        for doc in docs:
            batch = [doc]
            for t in transforms:
                next_batch = []
                for d in batch:
                    next_batch.extend(t.transform(d))
                batch = next_batch
            all_chunks.extend(batch)

        sink = JSONSink(sink_path, include_embeddings=embed)
        written = sink.write(all_chunks)

        progress.update(task, total=1, completed=1)

    elapsed = time.time() - start

    table = Table(title="Index Complete", border_style="green", show_header=False)
    table.add_column("Metric", style="dim", width=20)
    table.add_column("Value", style="bold green")
    table.add_row("Project type", project_type)
    table.add_row("Files indexed", str(len(docs)))
    table.add_row("Chunks created", str(len(all_chunks)))
    table.add_row("Written", str(written))
    table.add_row("Time", f"{elapsed:.2f}s")
    console.print(table)


# ─── WATCH ────────────────────────────────────────────────────────────────────


@app.command()
def watch(
    path: str = typer.Argument(".", help="Directory to watch"),
    sink_path: str = typer.Option("./ragpipe_output.json", "--sink-path", help="Output path"),
    chunk_size: int = typer.Option(512, "--chunk-size", "-c", help="Chunk size"),
    debounce: float = typer.Option(2.0, "--debounce", "-d", help="Debounce seconds"),
):
    _print_banner()
    console.print(f"[dim]Watching:[/dim] {path}")
    console.print(f"[dim]Output:[/dim]   {sink_path}")
    console.print(f"[dim]Debounce:[/dim] {debounce}s")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    try:
        from ragpipe.integrations.watcher import watch as _watch
        from ragpipe.integrations.indexer import index_project
        from ragpipe.transforms import RecursiveChunker
        from ragpipe.sinks import JSONSink

        def on_change(event_type: str, changed_path: str):
            console.print(f"[dim]{event_type}: {changed_path} — reindexing...[/dim]")
            docs = index_project(path)
            chunks = []
            for doc in docs:
                chunks.extend(RecursiveChunker(chunk_size=chunk_size).transform(doc))
            sink = JSONSink(sink_path)
            sink.write(chunks)
            console.print(f"[green]✓[/green] Reindexed {len(docs)} files → {len(chunks)} chunks")

        _watch(path, on_change=on_change, debounce=debounce)
    except ImportError:
        console.print(
            "[red]✗[/red] watchdog is required. Install with: [bold]pip install watchdog[/bold]"
        )
        raise typer.Exit(1)


# ─── SERVE ────────────────────────────────────────────────────────────────────


@app.command()
def serve(
    data_path: str = typer.Option("./ragpipe_output.json", "--data", "-d", help="Data file path"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(7642, "--port", "-p", help="Bind port"),
):
    _print_banner()
    console.print(f"[dim]Data:[/dim] {data_path}")
    console.print(f"[dim]URL:[/dim]  http://{host}:{port}")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    from ragpipe.integrations.server import serve as _serve

    _serve(data_path=data_path, host=host, port=port)


# ─── SEARCH (with fzf) ───────────────────────────────────────────────────────


@app.command()
def search(
    text: str = typer.Argument("", help="Search query (optional with --fzf)"),
    sink_path: str = typer.Option("./ragpipe_output.json", "--sink-path", help="Data file path"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
    mode: str = typer.Option("auto", "--mode", help="Search mode: auto, semantic, keyword"),
    fzf: bool = typer.Option(False, "--fzf", "-f", help="Use fzf for interactive search"),
):
    if not text and not fzf:
        console.print("[red]✗[/red] Provide a query or use --fzf for interactive mode.")
        raise typer.Exit(1)

    if fzf and not text:
        import subprocess

        data = json.loads(Path(sink_path).read_text()) if Path(sink_path).exists() else []
        if not data:
            console.print("[yellow]No data. Run ragpipe index first.[/yellow]")
            raise typer.Exit(1)
        items = "\n".join(d["content"][:100] for d in data)
        result = subprocess.run(
            ["fzf", "--prompt=RAGPipe> ", "--no-mouse", "--height=40%"],
            input=items,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise typer.Exit(0)
        text = result.stdout.strip()[:100]

    results = query(text=text, sink_path=sink_path, top_k=top_k, mode=mode)
    _results_table(text, results)


# ─── GIT HOOKS ────────────────────────────────────────────────────────────────

git_app = typer.Typer(name="git", help="Manage git hooks for auto-indexing.", no_args_is_help=True)
app.add_typer(git_app)


@git_app.command()
def hook(
    repo_path: str = typer.Argument(".", help="Git repo path"),
    sink_path: str = typer.Option("./ragpipe_output.json", "--sink-path", help="Output path"),
    chunk_size: int = typer.Option(512, "--chunk-size", "-c", help="Chunk size"),
):
    _print_banner()
    from ragpipe.integrations.git_hooks import install_hook

    try:
        install_hook(repo_path=repo_path, output_path=sink_path, chunk_size=chunk_size)
        console.print(
            f"[green]✓[/green] Git hook installed in [bold]{repo_path}/.git/hooks/post-commit[/bold]"
        )
        console.print("[dim]  Your codebase will auto-index after every commit.[/dim]")
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@git_app.command()
def remove(
    repo_path: str = typer.Argument(".", help="Git repo path"),
):
    from ragpipe.integrations.git_hooks import remove_hook

    try:
        remove_hook(repo_path=repo_path)
        console.print(f"[green]✓[/green] Git hook removed from [bold]{repo_path}[/bold]")
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@git_app.command("list")
def list_installed(
    repo_path: str = typer.Argument(".", help="Git repo path"),
):
    from ragpipe.integrations.git_hooks import list_hooks

    hooks = list_hooks(repo_path=repo_path)
    if not hooks:
        console.print("[dim]No RAGPipe hooks installed.[/dim]")
        return
    table = Table(title="Installed Hooks", border_style="cyan")
    table.add_column("Hook", style="cyan")
    table.add_column("Output", style="white")
    for h in hooks:
        table.add_row(h.get("hook_type", "?"), h.get("output_path", "?"))
    console.print(table)


# ─── VSCODE ───────────────────────────────────────────────────────────────────

vscode_app = typer.Typer(
    name="vscode", help="Generate VSCode workspace config.", no_args_is_help=True
)
app.add_typer(vscode_app)


@vscode_app.command()
def tasks(
    project_path: str = typer.Argument(".", help="Project path"),
):
    from ragpipe.integrations.vscode import generate_tasks

    try:
        generate_tasks(project_path=project_path)
        console.print(f"[green]✓[/green] Generated [bold].vscode/tasks.json[/bold]")
        console.print("[dim]  Open in VSCode and run Tasks → RAGPipe: Index Project[/dim]")
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@vscode_app.command()
def settings(
    project_path: str = typer.Argument(".vscode/settings.json", help="Settings path"),
    port: int = typer.Option(7642, "--port", "-p", help="Server port"),
):
    from ragpipe.integrations.vscode import generate_settings

    try:
        generate_settings(project_path=project_path, port=port)
        console.print(f"[green]✓[/green] Generated [bold]{project_path}[/bold]")
    except Exception as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


# ─── MACOS ────────────────────────────────────────────────────────────────────

macos_app = typer.Typer(name="macos", help="macOS-specific integrations.", no_args_is_help=True)
app.add_typer(macos_app)


@macos_app.command("spotlight")
def macos_spotlight(
    query_text: str = typer.Argument(..., help="Spotlight search query"),
    path: str = typer.Option("/", "--path", help="Search scope"),
):
    _print_banner()
    from ragpipe.integrations.macos import is_macos, spotlight_search

    if not is_macos():
        console.print("[red]✗[/red] macOS only.")
        raise typer.Exit(1)
    with console.status("[bold cyan]Searching via Spotlight..."):
        docs = spotlight_search(query_text, path=path)
    if not docs:
        console.print("[yellow]No results.[/yellow]")
        return
    table = Table(
        title=f'Spotlight: [magenta]"{query_text}"[/magenta]', border_style="cyan", show_lines=True
    )
    table.add_column("Path", style="cyan", max_width=60)
    table.add_column("Preview", style="white", max_width=80)
    for doc in docs[:20]:
        table.add_row(doc.metadata.get("path", "?"), doc.content[:120].replace("\n", " "))
    console.print(table)
    if len(docs) > 20:
        console.print(f"[dim]...and {len(docs) - 20} more[/dim]")


@macos_app.command("index")
def spotlight_index(
    path: str = typer.Argument(".", help="Directory to index via Spotlight"),
):
    _print_banner()
    from ragpipe.integrations.macos import is_macos, spotlight_index

    if not is_macos():
        console.print("[red]✗[/red] macOS only.")
        raise typer.Exit(1)
    with console.status("[bold cyan]Indexing via Spotlight..."):
        docs = spotlight_index(path)
    console.print(f"[green]✓[/green] Found [bold]{len(docs)}[/bold] files via Spotlight")


# ─── LINUX ────────────────────────────────────────────────────────────────────

linux_app = typer.Typer(name="linux", help="Linux-specific integrations.", no_args_is_help=True)
app.add_typer(linux_app)


@linux_app.command()
def service(
    name: str = typer.Option("ragpipe-serve", "--name", help="Service name"),
    data_path: str = typer.Option("./ragpipe_output.json", "--data", help="Data file path"),
    port: int = typer.Option(7642, "--port", "-p", help="Port"),
    user: str = typer.Option("", "--user", "-u", help="Run as user (default: current)"),
    install_flag: bool = typer.Option(False, "--install", help="Install to systemd"),
):
    from ragpipe.integrations.linux import is_linux, generate_systemd_service

    if not is_linux():
        console.print("[red]✗[/red] Linux only.")
        raise typer.Exit(1)
    content = generate_systemd_service(name=name, data_path=data_path, port=port, user=user or None)
    if install_flag:
        from ragpipe.integrations.linux import install_service

        try:
            result = install_service(content, name=name)
            console.print(f"[green]✓[/green] Service installed")
            for line in result.get("instructions", []):
                console.print(f"  [dim]{line}[/dim]")
        except Exception as e:
            console.print(f"[red]✗[/red] {e}")
            raise typer.Exit(1)
    else:
        console.print(content)
        console.print(f"\n[dim]Save to /etc/systemd/system/{name}.service and run:[/dim]")
        console.print(f"  [bold]sudo systemctl daemon-reload[/bold]")
        console.print(f"  [bold]sudo systemctl enable --now {name}[/bold]")


@linux_app.command()
def timer(
    project_path: str = typer.Argument(".", help="Project path to index"),
    name: str = typer.Option("ragpipe-index", "--name", help="Timer name"),
    interval: str = typer.Option(
        "hourly", "--interval", "-i", help="Interval: hourly, daily, weekly"
    ),
    install_flag: bool = typer.Option(False, "--install", help="Install to systemd"),
):
    from ragpipe.integrations.linux import is_linux, generate_systemd_timer

    if not is_linux():
        console.print("[red]✗[/red] Linux only.")
        raise typer.Exit(1)
    timer_content, service_content = generate_systemd_timer(
        name=name, project_path=project_path, interval=interval
    )
    if install_flag:
        from ragpipe.integrations.linux import install_service

        try:
            result = install_service(service_content, timer_content=timer_content, name=name)
            console.print(f"[green]✓[/green] Timer installed")
            for line in result.get("instructions", []):
                console.print(f"  [dim]{line}[/dim]")
        except Exception as e:
            console.print(f"[red]✗[/red] {e}")
            raise typer.Exit(1)
    else:
        console.print(f"[bold]Timer:[/bold]\n{timer_content}")
        console.print(f"\n[bold]Service:[/bold]\n{service_content}")
        console.print(f"\n[dim]Save to /etc/systemd/system/ and run:[/dim]")
        console.print(f"  [bold]sudo systemctl daemon-reload[/bold]")
        console.print(f"  [bold]sudo systemctl enable --now {name}.timer[/bold]")
