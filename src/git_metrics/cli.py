from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

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
    plugin_manager.discover_plugins()
    plugin_manager.activate_plugins(metrics)
    
    analyzer = GitAnalyzer(
        repo_path=str(repo),
        max_commits=max_commits,
        since_days=since_days,
        use_python=use_python,
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
    
    console.print(f"[bold]Total number of commits collected:[/bold] {len(commits)}")
    
    metrics_result = plugin_manager.calculate_metrics(commits)
    
    plugin_manager.display_metrics(metrics_result, limit)


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
    use_python: bool = typer.Option(
        False, "--use-python", help="Force using Python implementation instead of Rust"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show more detailed output"
    ),
):
    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()
    plugin_manager.activate_plugins(metrics)
    
    analyzer = GitAnalyzer(
        repo_path=str(repo),
        max_commits=max_commits,
        since_days=since_days,
        use_python=use_python,
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Collecting git history...", total=None)
        commits = analyzer.collect_history()
    
    console.print(f"[bold]Total number of commits collected:[/bold] {len(commits)}")
    
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
    
    impact = plugin_manager.analyze_impact(current_changes, metrics_result)
    
    plugin_manager.display_impact(impact)


@app.command("plugins")
def list_plugins():
    plugin_manager = PluginManager()
    plugins = plugin_manager.discover_plugins()
    
    console.print("\n[bold]Available metrics plugins:[/bold]")
    
    for plugin_id, plugin_class in plugins.items():
        plugin = plugin_class()
        console.print(f"  [green]{plugin_id}[/green]: {plugin.name} - {plugin.description}")


@app.callback()
def main():
    pass


if __name__ == "__main__":
    app()
