from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import box

from gitsect.core.analyzer import GitAnalyzer
from gitsect.plugins.manager import PluginManager

app = typer.Typer(help="Analyze git repository using research-backed metrics", add_completion=False)
console = Console()

def setup_analyzer(repo: Path, max_commits: Optional[int], since_days: Optional[int], use_python: bool, file_patterns: Optional[List[str]]):
    return GitAnalyzer(
        repo_path=str(repo),
        max_commits=max_commits,
        since_days=since_days,
        use_python=use_python,
        file_patterns=file_patterns,
    )

def collect_commits(analyzer: GitAnalyzer):
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Collecting git history...", total=None)
        return analyzer.collect_history()

def clear_cache(analyzer: GitAnalyzer):
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Clearing cache...", total=None)
        analyzer.clear_cache()

def display_repo_summary(repo: Path, max_commits: Optional[int], since_days: Optional[int], file_patterns: Optional[List[str]], commits: List[dict]):
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

def calculate_metrics(plugin_manager: PluginManager, commits: List[dict]):
    return plugin_manager.calculate_metrics(commits)

def collect_current_changes(analyzer: GitAnalyzer):
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Analyzing current changes...", total=None)
        return analyzer.get_current_changes()

def display_current_changes(current_changes: dict):
    changes_table = Table(title="Current Changes", box=box.ROUNDED, border_style="yellow")
    changes_table.add_column("File", style="blue")
    changes_table.add_column("Additions", justify="right", style="green")
    changes_table.add_column("Deletions", justify="right", style="red")
    changes_table.add_column("Total", justify="right")
    
    for filename, stats in current_changes.items():
        additions = stats.get("additions", 0)
        deletions = stats.get("deletions", 0)
        total = stats.get("total", additions + deletions)
        changes_table.add_row(filename, f"+{additions}", f"-{deletions}", str(total))
    
    console.print(changes_table)
    console.print()

def calculate_impact(plugin_manager: PluginManager, current_changes: dict, metrics_result: dict):
    return plugin_manager.analyze_impact(current_changes, metrics_result)

@app.command("metrics")
def show_metrics(
    repo: Path = typer.Option(".", "--repo", "-r", help="Path to git repository"),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit for displayed items"),
    metrics: Optional[List[str]] = typer.Option(None, "--metrics", "-m", help="Specific metrics to analyze (omit for all)"),
    max_commits: Optional[int] = typer.Option(None, "--max-commits", help="Maximum number of commits to analyze"),
    since_days: Optional[int] = typer.Option(None, "--since-days", help="Analyze commits from the last N days"),
    file_patterns: Optional[List[str]] = typer.Option(None, "--files", "-f", help="File patterns to filter (e.g. '*.py', 'src/*')"),
    use_python: bool = typer.Option(False, "--use-python", help="Force using Python implementation instead of Rust"),
    clear: bool = typer.Option(False, "--clear-cache", help="Clear the commit data cache"),
):
    plugin_manager = PluginManager()
    plugin_manager.activate_plugins(metrics)
    
    analyzer = setup_analyzer(repo, max_commits, since_days, use_python, file_patterns)
    
    if clear:
        clear_cache(analyzer)
        return
    
    commits = collect_commits(analyzer)
    display_repo_summary(repo, max_commits, since_days, file_patterns, commits)
    
    metrics_result = calculate_metrics(plugin_manager, commits)
    plugin_manager.display_metrics(metrics_result, limit, console=console)
    
@app.command("impact")
def analyze_impact(
    repo: Path = typer.Option(".", "--repo", "-r", help="Path to git repository"),
    metrics: Optional[List[str]] = typer.Option(None, "--metrics", "-m", help="Specific metrics to analyze (omit for all)"),
    max_commits: Optional[int] = typer.Option(None, "--max-commits", help="Maximum number of commits to analyze"),
    since_days: Optional[int] = typer.Option(None, "--since-days", help="Analyze commits from the last N days"),
    file_patterns: Optional[List[str]] = typer.Option(None, "--files", "-f", help="File patterns to filter (e.g. '*.py', 'src/*')"),
    use_python: bool = typer.Option(False, "--use-python", help="Force using Python implementation instead of Rust"),
):
    plugin_manager = PluginManager()
    plugin_manager.activate_plugins(metrics)
    
    analyzer = setup_analyzer(repo, max_commits, since_days, use_python, file_patterns)
    
    commits = collect_commits(analyzer)
    metrics_result = calculate_metrics(plugin_manager, commits)
    
    current_changes = collect_current_changes(analyzer)
    
    if not current_changes:
        console.print("\n[yellow]No uncommitted changes found.[/yellow]")
        return
    
    display_current_changes(current_changes)
    impact = calculate_impact(plugin_manager, current_changes, metrics_result)
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
