from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.tree import Tree
from rich.text import Text

from git_metrics.core.analyzer import GitAnalyzer
from git_metrics.plugins.manager import PluginManager

app = typer.Typer(
    help="Analyze git repository using research-backed metrics",
    add_completion=False,
)

console = Console()

@app.command("metrics")
def show_metrics(
    repo: Path = typer.Option(
        ".", "--repo", "-r", help="Path to git repository"
    ),
    limit: int = typer.Option(
        10, "--limit", "-l", help="Limit for displayed items"
    ),
    metrics: Optional[List[str]] = typer.Option(
        None, "--metrics", "-m", help="Specific metrics to analyze (omit for all)"
    ),
    max_commits: Optional[int] = typer.Option(
        None, "--max-commits", help="Maximum number of commits to analyze"
    ),
    since_days: Optional[int] = typer.Option(
        None, "--since-days", help="Analyze commits from the last N days"
    ),
    file_patterns: Optional[List[str]] = typer.Option(
        None, "--files", "-f", help="File patterns to filter (e.g. '*.py', 'src/*')"
    ),
    use_python: bool = typer.Option(
        False, "--use-python", help="Force using Python implementation instead of Rust"
    ),
    clear_cache: bool = typer.Option(
        False, "--clear-cache", help="Clear the commit data cache"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show more detailed output"
    ),
):
    plugin_manager = PluginManager()
    plugin_manager.activate_plugins(metrics)
    
    analyzer = GitAnalyzer(
        repo_path=str(repo),
        max_commits=max_commits,
        since_days=since_days,
        use_python=use_python,
        file_patterns=file_patterns,
    )
    
    if clear_cache:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Clearing cache...", total=None)
            analyzer.clear_cache()
        console.print("[green]Cache cleared successfully.[/green]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Collecting git history...", total=None)
        commits = analyzer.collect_history()
    
    repo_summary = Table.grid(padding=(0, 1))
    repo_summary.add_row("[bold cyan]Repository:", f"[white]{repo}")
    repo_summary.add_row("[bold cyan]Commits analyzed:", f"[white]{len(commits)}")
    if max_commits:
        repo_summary.add_row("[bold cyan]Commit limit:", f"[white]{max_commits}")
    if since_days:
        repo_summary.add_row("[bold cyan]Time range:", f"[white]Last {since_days} days")
    if file_patterns:
        repo_summary.add_row("[bold cyan]File patterns:", f"[white]{', '.join(file_patterns)}")
    
    console.print(Panel(repo_summary, title="Repository Analysis", border_style="blue"))
    
    metrics_result = plugin_manager.calculate_metrics(commits)
    
    plugin_manager.display_metrics(metrics_result, limit, console=console)


@app.command("impact")
def analyze_impact(
    repo: Path = typer.Option(
        ".", "--repo", "-r", help="Path to git repository"
    ),
    metrics: Optional[List[str]] = typer.Option(
        None, "--metrics", "-m", help="Specific metrics to analyze (omit for all)"
    ),
    max_commits: Optional[int] = typer.Option(
        None, "--max-commits", help="Maximum number of commits to analyze"
    ),
    since_days: Optional[int] = typer.Option(
        None, "--since-days", help="Analyze commits from the last N days"
    ),
    file_patterns: Optional[List[str]] = typer.Option(
        None, "--files", "-f", help="File patterns to filter (e.g. '*.py', 'src/*')"
    ),
    use_python: bool = typer.Option(
        False, "--use-python", help="Force using Python implementation instead of Rust"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show more detailed output"
    ),
):
    plugin_manager = PluginManager()
    plugin_manager.activate_plugins(metrics)
    
    analyzer = GitAnalyzer(
        repo_path=str(repo),
        max_commits=max_commits,
        since_days=since_days,
        use_python=use_python,
        file_patterns=file_patterns,
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Collecting git history...", total=None)
        commits = analyzer.collect_history()
    
    metrics_result = plugin_manager.calculate_metrics(commits)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing current changes...", total=None)
        current_changes = analyzer.get_current_changes()
    
    if not current_changes:
        console.print("\n[yellow]No uncommitted changes found.[/yellow]")
        return
    
    changes_table = Table(title="Current Changes", box=box.ROUNDED, border_style="yellow")
    changes_table.add_column("File", style="blue")
    changes_table.add_column("Additions", justify="right", style="green")
    changes_table.add_column("Deletions", justify="right", style="red")
    changes_table.add_column("Total", justify="right")
    
    for filename, stats in current_changes.items():
        additions = stats.get("additions", 0)
        deletions = stats.get("deletions", 0)
        total = stats.get("total", additions + deletions)
        changes_table.add_row(
            filename,
            f"+{additions}",
            f"-{deletions}",
            str(total)
        )
    
    console.print(changes_table)
    console.print()
    
    impact = plugin_manager.analyze_impact(current_changes, metrics_result)
    
    plugin_manager.display_impact(impact, console=console)


@app.command("plugins")
def list_plugins():
    plugin_manager = PluginManager()
    plugins = plugin_manager.discover_plugins()
    
    table = Table(title="Available Metrics Plugins", box=box.ROUNDED, border_style="cyan")
    table.add_column("ID", style="green")
    table.add_column("Name", style="blue")
    table.add_column("Description")
    
    for plugin_id, plugin_class in plugins.items():
        plugin = plugin_class()
        table.add_row(plugin_id, plugin.name, plugin.description)
    
    console.print(table)


@app.callback()
def main():
    pass


if __name__ == "__main__":
    app()
