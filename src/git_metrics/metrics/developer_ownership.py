from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Set, Tuple, Optional

from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.text import Text

from git_metrics.plugins.interface import MetricPlugin


class DeveloperOwnershipMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Developer Ownership"
    
    @property
    def description(self) -> str:
        return "Measures the concentration of changes among developers."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        author_changes: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        file_authors: DefaultDict[str, Set[str]] = defaultdict(set)
        
        for commit in commits:
            author = commit["author"]
            
            for file_change in commit["files"]:
                filename = file_change["filename"]
                author_changes[filename][author] += 1
                file_authors[filename].add(author)
        
        file_ownership: Dict[str, Dict[str, Any]] = {}
        for filename, authors in file_authors.items():
            if not authors:
                continue
                
            author_counts: Dict[str, int] = {}
            for author in authors:
                author_counts[author] = author_changes[filename][author]
            
            total_changes = sum(author_counts.values())
            if total_changes == 0:
                continue
                
            dominant_author = max(author_counts.items(), key=lambda x: x[1])
            ownership = dominant_author[1] / total_changes
            
            file_ownership[filename] = {
                "dominant_author": dominant_author[0],
                "ownership_ratio": ownership,
                "contributor_count": len(authors),
                "author_changes": author_counts,
                "total_changes": total_changes
            }
        
        sorted_ownership = dict(sorted(
            file_ownership.items(),
            key=lambda x: x[1]["ownership_ratio"],
            reverse=True
        ))
        
        return sorted_ownership
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        impact: Dict[str, Dict[str, Any]] = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = {
                "metrics": {}
            }
            
            if filename not in metric_result:
                impact[filename]["new_file"] = True
                continue
            
            ownership_data = metric_result[filename]
            dominant_author = ownership_data["dominant_author"]
            ownership_ratio = ownership_data["ownership_ratio"]
            contributor_count = ownership_data["contributor_count"]
            
            authors_sorted = sorted(
                ownership_data["author_changes"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_contributors = authors_sorted[:3]
            
            impact[filename]["metrics"] = {
                "dominant_author": dominant_author,
                "ownership_ratio": ownership_ratio,
                "contributor_count": contributor_count,
                "total_changes": ownership_data["total_changes"],
                "top_contributors": top_contributors,
                "ownership_category": self._categorize_ownership(ownership_ratio, contributor_count)
            }
        
        return impact
    
    def _categorize_ownership(self, ratio: float, contributors: int) -> str:
        if ratio > 0.8 and contributors == 1:
            return "exclusive"
        elif ratio > 0.8:
            return "strong"
        elif ratio > 0.5:
            return "moderate"
        elif ratio > 0.3:
            return "shared"
        else:
            return "dispersed"
    
    def display_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10, console: Optional[Any] = None) -> None:
        if console is None:
            self._print_result(result, limit)
            return
        
        table = Table(
            title="Developer Ownership Analysis",
            box=box.ROUNDED,
            title_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Rank", justify="right", style="cyan", width=5)
        table.add_column("File", style="blue")
        table.add_column("Owner", style="green")
        table.add_column("Ownership", justify="right", style="magenta")
        table.add_column("Contributors", justify="right", style="yellow")
        table.add_column("Distribution", width=30)
        
        for i, (filename, data) in enumerate(list(result.items())[:limit]):
            bar = ProgressBar(total=100, completed=int(data["ownership_ratio"] * 100), width=30)
            
            table.add_row(
                f"#{i+1}",
                filename,
                data["dominant_author"],
                f"{data['ownership_ratio']*100:.1f}%",
                f"{data['contributor_count']}",
                bar
            )
        
        console.print(table)
    
    def _print_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10) -> None:
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by ownership strength:")
        
        items = list(result.items())[:limit]
        for i, (filename, data) in enumerate(items):
            print(f"{i+1}. {filename}")
            print(f"   Owner: {data['dominant_author']} ({data['ownership_ratio']*100:.1f}%)")
            print(f"   Contributors: {data['contributor_count']}")
    
    def display_impact(self, impact: Dict[str, Dict[str, Any]], console: Optional[Any] = None) -> None:
        if console is None:
            self._print_impact(impact)
            return
        
        table = Table(
            title="Developer Ownership Impact Analysis",
            box=box.ROUNDED,
            title_style="bold yellow",
            border_style="yellow"
        )
        
        table.add_column("File", style="blue")
        table.add_column("Owner", style="green")
        table.add_column("Ownership", justify="right", style="magenta")
        table.add_column("Contributors", justify="right", style="yellow")
        table.add_column("Category", justify="center")
        
        has_entries = False
        for filename, data in impact.items():
            if data.get("new_file", False):
                table.add_row(
                    filename,
                    "None",
                    "N/A",
                    "N/A",
                    "[bold green]NEW FILE[/bold green]"
                )
                has_entries = True
            elif "metrics" in data:
                metrics = data["metrics"]
                
                category = metrics.get("ownership_category", "unknown")
                category_style = {
                    "exclusive": "[bold blue]EXCLUSIVE[/bold blue]",
                    "strong": "[blue]STRONG[/blue]",
                    "moderate": "[cyan]MODERATE[/cyan]",
                    "shared": "[green]SHARED[/green]",
                    "dispersed": "[yellow]DISPERSED[/yellow]"
                }.get(category, "[grey]UNKNOWN[/grey]")
                
                table.add_row(
                    filename,
                    metrics.get("dominant_author", "Unknown"),
                    f"{metrics.get('ownership_ratio', 0)*100:.1f}%",
                    str(metrics.get("contributor_count", 0)),
                    category_style
                )
                has_entries = True
        
        if has_entries:
            console.print(table)
            
            console.print()
            for filename, data in impact.items():
                if "metrics" in data and "top_contributors" in data["metrics"]:
                    top_contributors = data["metrics"]["top_contributors"]
                    total_changes = data["metrics"]["total_changes"]
                    
                    if top_contributors:
                        contrib_table = Table(
                            title=f"Top Contributors: {filename}",
                            box=box.SIMPLE,
                            title_style="bold blue",
                            border_style="blue"
                        )
                        
                        contrib_table.add_column("Developer", style="green")
                        contrib_table.add_column("Changes", justify="right", style="cyan")
                        contrib_table.add_column("Percentage", justify="right", style="magenta")
                        contrib_table.add_column("Distribution", width=30)
                        
                        for author, changes in top_contributors:
                            percentage = changes / total_changes if total_changes > 0 else 0
                            bar = ProgressBar(total=100, completed=int(percentage * 100), width=30)
                            
                            contrib_table.add_row(
                                author,
                                str(changes),
                                f"{percentage*100:.1f}%",
                                bar
                            )
                        
                        console.print(contrib_table)
                        console.print()
        else:
            console.print(Panel("No ownership impact data to display", border_style="yellow"))
    
    def _print_impact(self, impact: Dict[str, Dict[str, Any]]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        for filename, data in impact.items():
            if "metrics" in data:
                metrics = data["metrics"]
                print(f"\nFile: {filename}")
                print(f"  Dominant author: {metrics.get('dominant_author', 'Unknown')}")
                print(f"  Ownership ratio: {metrics.get('ownership_ratio', 0)*100:.1f}%")
                print(f"  Contributors: {metrics.get('contributor_count', 0)}")
                print(f"  Category: {metrics.get('ownership_category', 'unknown').upper()}")
                
                if "top_contributors" in metrics:
                    print("  Top contributors:")
                    for author, changes in metrics["top_contributors"]:
                        percentage = changes / metrics["total_changes"] if metrics["total_changes"] > 0 else 0
                        print(f"    - {author}: {changes} changes ({percentage*100:.1f}%)")
