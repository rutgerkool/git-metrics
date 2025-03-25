from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Set, Optional

from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.text import Text
from rich.layout import Layout
from rich.console import Console

from git_metrics.plugins.interface import MetricPlugin


class KnowledgeDistributionMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Knowledge Distribution"
    
    @property
    def description(self) -> str:
        return "Analyzes how knowledge is spread across the team."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        file_changes: DefaultDict[str, int] = defaultdict(int)
        author_changes: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        author_commit_count: DefaultDict[str, int] = defaultdict(int)
        file_authors: DefaultDict[str, Set[str]] = defaultdict(set)
        
        for commit in commits:
            author = commit["author"]
            author_commit_count[author] += 1
            
            for file_change in commit["files"]:
                filename = file_change["filename"]
                file_changes[filename] += 1
                author_changes[author][filename] += 1
                file_authors[filename].add(author)
        
        file_ownership: Dict[str, Dict[str, Any]] = {}
        for filename, authors in file_authors.items():
            if not authors:
                continue
                
            author_counts: Dict[str, int] = {}
            for author in authors:
                author_counts[author] = author_changes[author][filename]
            
            total_changes = sum(author_counts.values())
            if total_changes == 0:
                continue
                
            dominant_author = max(author_counts.items(), key=lambda x: x[1])
            ownership = dominant_author[1] / total_changes
            
            file_ownership[filename] = {
                "dominant_author": dominant_author[0],
                "ownership_ratio": ownership,
                "contributor_count": len(authors)
            }
        
        all_files = set(file_changes.keys())
        all_authors = set(author_commit_count.keys())
        
        team_knowledge: Dict[str, Dict[str, Any]] = {}
        for author in all_authors:
            author_files = set(author_changes[author].keys())
            
            knowledge_coverage = len(author_files) / len(all_files) if all_files else 0
            
            knowledge_depth = 0
            touched_files = 0
            for filename in author_files:
                if filename in file_ownership and file_ownership[filename]["dominant_author"] == author:
                    knowledge_depth += file_ownership[filename]["ownership_ratio"]
                    touched_files += 1
            
            avg_knowledge_depth = knowledge_depth / touched_files if touched_files > 0 else 0
            
            owned_files = [f for f in author_files if f in file_ownership and 
                           file_ownership[f]["dominant_author"] == author]
            
            bus_factor_contribution = len(owned_files) / len(all_files) if all_files else 0
            
            team_knowledge[author] = {
                "coverage": knowledge_coverage,
                "depth": avg_knowledge_depth,
                "owned_files": len(owned_files),
                "files_changed": len(author_files),
                "commit_count": author_commit_count[author],
                "bus_factor_contribution": bus_factor_contribution
            }
        
        sorted_knowledge = dict(sorted(
            team_knowledge.items(),
            key=lambda x: x[1]["coverage"] * x[1]["depth"],
            reverse=True
        ))
        
        team_metrics = {
            "bus_factor": self._calculate_bus_factor(sorted_knowledge),
            "knowledge_redundancy": self._calculate_knowledge_redundancy(all_files, file_authors),
            "authors": sorted_knowledge,
            "file_ownership": file_ownership,
            "file_count": len(all_files),
            "author_count": len(all_authors)
        }
        
        return team_metrics
    
    def _calculate_bus_factor(self, team_knowledge: Dict[str, Dict[str, Any]]) -> int:
        sorted_by_risk = sorted(
            team_knowledge.items(),
            key=lambda x: x[1]["bus_factor_contribution"],
            reverse=True
        )
        
        cumulative = 0
        bus_factor = 0
        
        for author, data in sorted_by_risk:
            cumulative += data["bus_factor_contribution"]
            bus_factor += 1
            
            if cumulative >= 0.5:
                break
        
        return bus_factor
    
    def _calculate_knowledge_redundancy(self, all_files: Set[str], file_authors: DefaultDict[str, Set[str]]) -> float:
        if not all_files:
            return 0
            
        total_authors = sum(len(authors) for authors in file_authors.values())
        return total_authors / len(all_files)
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        impact = {
            "team_metrics": {},
            "file_metrics": {}
        }
        
        modified_files = list(current_changes.keys())
        
        team_metrics = {
            "bus_factor": metric_result["bus_factor"],
            "knowledge_redundancy": metric_result["knowledge_redundancy"],
            "file_count": metric_result["file_count"],
            "author_count": metric_result["author_count"],
            "risk_level": self._calculate_team_risk_level(metric_result["bus_factor"], metric_result["knowledge_redundancy"])
        }
        impact["team_metrics"] = team_metrics
        
        file_ownership = metric_result.get("file_ownership", {})
        authors = metric_result.get("authors", {})
        
        for filename in modified_files:
            impact["file_metrics"][filename] = {
                "metrics": {}
            }
            
            if filename not in file_ownership:
                impact["file_metrics"][filename]["new_file"] = True
                continue
            
            dominant_author = file_ownership[filename]["dominant_author"]
            ownership_ratio = file_ownership[filename]["ownership_ratio"]
            contributor_count = file_ownership[filename]["contributor_count"]
            
            author_data = authors.get(dominant_author, {})
            knowledge_depth = author_data.get("depth", 0)
            knowledge_coverage = author_data.get("coverage", 0)
            
            impact["file_metrics"][filename]["metrics"] = {
                "dominant_author": dominant_author,
                "ownership_ratio": ownership_ratio,
                "contributor_count": contributor_count,
                "author_knowledge_depth": knowledge_depth,
                "author_knowledge_coverage": knowledge_coverage,
                "knowledge_risk": self._calculate_knowledge_risk(ownership_ratio, contributor_count, knowledge_depth)
            }
        
        return impact
    
    def _calculate_team_risk_level(self, bus_factor, redundancy):
        if bus_factor <= 1:
            return "critical"
        elif bus_factor <= 2:
            return "high"
        elif redundancy < 1.5:
            return "medium"
        elif bus_factor <= 3:
            return "elevated"
        else:
            return "low"
    
    def _calculate_knowledge_risk(self, ownership_ratio, contributor_count, knowledge_depth):
        if ownership_ratio > 0.9 and contributor_count == 1 and knowledge_depth > 0.8:
            return "critical"
        elif ownership_ratio > 0.8 and contributor_count <= 2:
            return "high"
        elif contributor_count < 3 or ownership_ratio > 0.7:
            return "medium"
        elif contributor_count < 4:
            return "elevated"
        else:
            return "low"
    
    def display_result(self, result: Dict[str, Any], limit: int = 5, console: Optional[Any] = None) -> None:
        if console is None:
            self._print_result(result, limit)
            return
        
        team_table = Table(
            title="Team Knowledge Distribution",
            box=box.ROUNDED,
            title_style="bold blue",
            border_style="blue"
        )
        
        team_table.add_column("Metric", style="cyan")
        team_table.add_column("Value", style="green")
        team_table.add_column("Description", style="yellow")
        
        bus_factor = result["bus_factor"]
        knowledge_redundancy = result["knowledge_redundancy"]
        
        bus_factor_style = "green"
        if bus_factor <= 1:
            bus_factor_style = "bold red"
        elif bus_factor <= 2:
            bus_factor_style = "red"
        elif bus_factor <= 3:
            bus_factor_style = "yellow"
            
        team_table.add_row(
            "Bus Factor",
            f"[{bus_factor_style}]{bus_factor}[/{bus_factor_style}]",
            "Number of developers whose absence would risk project stalling"
        )
        
        redundancy_style = "green"
        if knowledge_redundancy < 1.2:
            redundancy_style = "red"
        elif knowledge_redundancy < 1.5:
            redundancy_style = "yellow"
            
        team_table.add_row(
            "Knowledge Redundancy",
            f"[{redundancy_style}]{knowledge_redundancy:.2f}[/{redundancy_style}]",
            "Average number of developers familiar with each file"
        )
        
        team_table.add_row(
            "Files",
            str(result.get("file_count", 0)),
            "Total files in repository"
        )
        
        team_table.add_row(
            "Contributors",
            str(result.get("author_count", 0)),
            "Total contributors to repository"
        )
        
        console.print(team_table)
        console.print()
        
        knowledge_table = Table(
            title="Developer Knowledge Distribution",
            box=box.ROUNDED,
            title_style="bold blue", 
            border_style="blue"
        )
        
        knowledge_table.add_column("Rank", justify="right", style="cyan", width=5)
        knowledge_table.add_column("Developer", style="blue")
        knowledge_table.add_column("Coverage", justify="right", style="green")
        knowledge_table.add_column("Depth", justify="right", style="yellow")
        knowledge_table.add_column("Owned Files", justify="right", style="magenta")
        knowledge_table.add_column("Commits", justify="right")
        
        authors = result.get("authors", {})
        for i, (author, data) in enumerate(list(authors.items())[:limit]):
            knowledge_table.add_row(
                f"#{i+1}",
                author,
                f"{data['coverage']*100:.1f}%",
                f"{data['depth']*100:.1f}%",
                str(data['owned_files']),
                str(data['commit_count'])
            )
        
        console.print(knowledge_table)
    
    def _print_result(self, result: Dict[str, Any], limit: int = 5) -> None:
        print(f"\n=== {self.name} ===")
        
        print("\nTeam-level metrics:")
        print(f"  Bus Factor: {result['bus_factor']} developers")
        print(f"  Knowledge Redundancy: {result['knowledge_redundancy']:.2f} average developers per file")
        
        print(f"\nTop {limit} developers by knowledge distribution:")
        
        items = list(result["authors"].items())[:limit]
        for i, (author, data) in enumerate(items):
            print(f"{i+1}. {author}")
            print(f"   Knowledge Coverage: {data['coverage']*100:.1f}% of codebase")
            print(f"   Knowledge Depth: {data['depth']*100:.1f}% avg ownership")
            print(f"   Bus Factor Contribution: {data['bus_factor_contribution']*100:.1f}% of codebase owned")
            print(f"   Activity: {data['commit_count']} commits, {data['files_changed']} files changed")
    
    def display_impact(self, impact: Dict[str, Any], console: Optional[Any] = None) -> None:
        if console is None:
            self._print_impact(impact)
            return
        
        team_metrics = impact.get("team_metrics", {})
        bus_factor = team_metrics.get("bus_factor", 0)
        redundancy = team_metrics.get("knowledge_redundancy", 0)
        risk_level = team_metrics.get("risk_level", "unknown")
        
        risk_style = {
            "critical": "[bold red]CRITICAL[/bold red]",
            "high": "[red]HIGH[/red]",
            "medium": "[yellow]MEDIUM[/yellow]",
            "elevated": "[yellow]ELEVATED[/yellow]",
            "low": "[green]LOW[/green]"
        }.get(risk_level, "[grey]UNKNOWN[/grey]")
        
        team_table = Table(
            title="Team Knowledge Impact",
            box=box.ROUNDED,
            title_style="bold yellow",
            border_style="yellow"
        )
        
        team_table.add_column("Metric", style="cyan")
        team_table.add_column("Value", style="green")
        team_table.add_column("Risk Level", style="yellow")
        
        team_table.add_row(
            "Bus Factor",
            f"{bus_factor}",
            risk_style
        )
        
        team_table.add_row(
            "Knowledge Redundancy",
            f"{redundancy:.2f}",
            ""
        )
        
        console.print(team_table)
        console.print()
        
        file_metrics = impact.get("file_metrics", {})
        
        if not file_metrics:
            console.print(Panel("No knowledge distribution impact data to display", border_style="yellow"))
            return
        
        file_table = Table(
            title="Knowledge Distribution Impact per File",
            box=box.ROUNDED,
            title_style="bold yellow",
            border_style="yellow"
        )
        
        file_table.add_column("File", style="blue")
        file_table.add_column("Owner", style="green")
        file_table.add_column("Ownership", justify="right", style="magenta")
        file_table.add_column("Contributors", justify="right", style="cyan")
        file_table.add_column("Risk Level", justify="center")
        
        has_entries = False
        for filename, data in file_metrics.items():
            if data.get("new_file", False):
                file_table.add_row(
                    filename,
                    "None",
                    "N/A",
                    "N/A",
                    "[bold green]NEW FILE[/bold green]"
                )
                has_entries = True
            elif "metrics" in data:
                metrics = data["metrics"]
                risk = metrics.get("knowledge_risk", "unknown")
                
                risk_style = {
                    "critical": "[bold red]CRITICAL[/bold red]",
                    "high": "[red]HIGH[/red]",
                    "medium": "[yellow]MEDIUM[/yellow]",
                    "elevated": "[yellow]ELEVATED[/yellow]",
                    "low": "[green]LOW[/green]"
                }.get(risk, "[grey]UNKNOWN[/grey]")
                
                file_table.add_row(
                    filename,
                    metrics.get("dominant_author", "Unknown"),
                    f"{metrics.get('ownership_ratio', 0)*100:.1f}%",
                    str(metrics.get("contributor_count", 0)),
                    risk_style
                )
                has_entries = True
        
        if has_entries:
            console.print(file_table)
    
    def _print_impact(self, impact: Dict[str, Any]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        team_metrics = impact.get("team_metrics", {})
        if team_metrics:
            print("\nTeam-level metrics:")
            print(f"  Bus Factor: {team_metrics.get('bus_factor', 0)}")
            print(f"  Knowledge Redundancy: {team_metrics.get('knowledge_redundancy', 0):.2f}")
            print(f"  Risk Level: {team_metrics.get('risk_level', 'unknown').upper()}")
        
        file_metrics = impact.get("file_metrics", {})
        if file_metrics:
            print("\nFile-level metrics:")
            for filename, data in file_metrics.items():
                if "metrics" in data:
                    metrics = data["metrics"]
                    print(f"\n  File: {filename}")
                    print(f"    Owner: {metrics.get('dominant_author', 'Unknown')}")
                    print(f"    Ownership: {metrics.get('ownership_ratio', 0)*100:.1f}%")
                    print(f"    Contributors: {metrics.get('contributor_count', 0)}")
                    print(f"    Risk Level: {metrics.get('knowledge_risk', 'unknown').upper()}")
