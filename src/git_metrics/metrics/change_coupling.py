from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Any, Tuple, DefaultDict, Set, Optional

import networkx as nx
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich.progress_bar import ProgressBar

from git_metrics.plugins.interface import MetricPlugin


class ChangeCouplingMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Change Coupling"
    
    @property
    def description(self) -> str:
        return "Measures how frequently files change together."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        file_changes: DefaultDict[str, int] = defaultdict(int)
        commit_files: List[List[str]] = []
        
        for commit in commits:
            files_in_commit: List[str] = []
            
            for file_change in commit["files"]:
                filename = file_change["filename"]
                files_in_commit.append(filename)
                file_changes[filename] += 1
            
            if files_in_commit:
                commit_files.append(files_in_commit)
        
        coupling_graph = nx.Graph()
        for filename in file_changes.keys():
            coupling_graph.add_node(filename)
        
        file_coupling: DefaultDict[Tuple[str, str], int] = defaultdict(int)
        for files in commit_files:
            for file1, file2 in combinations(files, 2):
                if file1 != file2:
                    pair = tuple(sorted([file1, file2]))
                    file_coupling[pair] += 1
                    coupling_graph.add_edge(file1, file2, weight=file_coupling[pair])
        
        normalized_coupling: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for pair, count in file_coupling.items():
            file1, file2 = pair
            f1_changes = file_changes[file1]
            f2_changes = file_changes[file2]
            union = f1_changes + f2_changes - count
            jaccard = count / union if union > 0 else 0
            normalized_coupling[pair] = {
                "count": count,
                "jaccard": jaccard,
                "file1_changes": f1_changes,
                "file2_changes": f2_changes
            }
        
        sorted_coupling = dict(sorted(
            normalized_coupling.items(),
            key=lambda x: x[1]["jaccard"],
            reverse=True
        ))
        
        result = {
            "coupling": sorted_coupling,
            "file_changes": file_changes,
            "graph": coupling_graph
        }
        
        return result
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        impact: Dict[str, Dict[str, Any]] = {}
        
        modified_files = list(current_changes.keys())
        coupling_data = metric_result["coupling"]
        
        for filename in modified_files:
            impact[filename] = {
                "metrics": {},
                "coupled_files": {
                    "modified": [],
                    "unmodified": []
                }
            }
            
            if filename not in metric_result["file_changes"]:
                impact[filename]["new_file"] = True
                continue
            
            max_coupling = 0
            avg_coupling = 0
            coupling_count = 0
            
            for pair, data in coupling_data.items():
                if filename in pair:
                    other_file = pair[0] if pair[1] == filename else pair[1]
                    coupling_strength = data["jaccard"]
                    
                    max_coupling = max(max_coupling, coupling_strength)
                    avg_coupling += coupling_strength
                    coupling_count += 1
                    
                    if other_file in modified_files:
                        impact[filename]["coupled_files"]["modified"].append({
                            "file": other_file,
                            "strength": coupling_strength,
                            "count": data["count"]
                        })
                    else:
                        impact[filename]["coupled_files"]["unmodified"].append({
                            "file": other_file,
                            "strength": coupling_strength,
                            "count": data["count"]
                        })
                        
            impact[filename]["coupled_files"]["modified"].sort(key=lambda x: x["strength"], reverse=True)
            impact[filename]["coupled_files"]["unmodified"].sort(key=lambda x: x["strength"], reverse=True)
            
            avg_coupling = avg_coupling / coupling_count if coupling_count > 0 else 0
            strong_unmodified = sum(1 for f in impact[filename]["coupled_files"]["unmodified"] if f["strength"] > 0.5)
            
            impact[filename]["metrics"] = {
                "max_coupling": max_coupling,
                "avg_coupling": avg_coupling,
                "total_coupled_files": coupling_count,
                "modified_coupled_files": len(impact[filename]["coupled_files"]["modified"]),
                "unmodified_coupled_files": len(impact[filename]["coupled_files"]["unmodified"]),
                "strong_unmodified": strong_unmodified,
                "risk_level": self._calculate_risk_level(max_coupling, strong_unmodified)
            }
        
        return impact
    
    def _calculate_risk_level(self, max_coupling, strong_unmodified):
        if max_coupling > 0.8 and strong_unmodified > 0:
            return "critical"
        elif max_coupling > 0.7 and strong_unmodified > 0:
            return "high"
        elif max_coupling > 0.5 or strong_unmodified > 1:
            return "medium"
        elif max_coupling > 0.3:
            return "elevated"
        else:
            return "low"
    
    def display_result(self, result: Dict[str, Any], limit: int = 10, console: Optional[Any] = None) -> None:
        if console is None:
            self._print_result(result, limit)
            return
        
        coupling_data = result["coupling"]
        
        table = Table(
            title="File Coupling Analysis",
            box=box.ROUNDED,
            title_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Rank", justify="right", style="cyan", width=5)
        table.add_column("File Pair", style="blue")
        table.add_column("Coupling", justify="right", style="magenta")
        table.add_column("Co-Changes", justify="right", style="green")
        table.add_column("Strength", width=30)
        
        for i, (pair, data) in enumerate(list(coupling_data.items())[:limit]):
            file1, file2 = pair
            
            short_file1 = file1.split("/")[-1]
            short_file2 = file2.split("/")[-1]
            
            bar = ProgressBar(total=100, completed=int(data["jaccard"] * 100), width=30)
            
            table.add_row(
                f"#{i+1}",
                f"{short_file1} ↔ {short_file2}",
                f"{data['jaccard']:.2f}",
                str(data["count"]),
                bar
            )
        
        console.print(table)
    
    def _print_result(self, result: Dict[str, Any], limit: int = 10) -> None:
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} strongest file couplings:")
        
        items = list(result["coupling"].items())[:limit]
        for i, (pair, data) in enumerate(items):
            print(f"{i+1}. {pair[0]} ↔ {pair[1]}: {data['jaccard']:.2f}")
            print(f"   Co-changed {data['count']} times")
    
    def display_impact(self, impact: Dict[str, Dict[str, Any]], console: Optional[Any] = None) -> None:
        if console is None:
            self._print_impact(impact)
            return
        
        panel = Panel(
            "[bold]File Coupling Impact Analysis[/bold]", 
            border_style="yellow",
            title_align="left"
        )
        console.print(panel)
        
        for filename, data in impact.items():
            if data.get("new_file", False):
                file_panel = Panel(
                    f"[bold green]NEW FILE[/bold green]",
                    title=f"[blue]{filename}[/blue]",
                    border_style="green",
                    width=100
                )
                console.print(file_panel)
                continue
                
            if "metrics" not in data or "coupled_files" not in data:
                continue
                
            metrics = data["metrics"]
            coupled_modified = data["coupled_files"]["modified"]
            coupled_unmodified = data["coupled_files"]["unmodified"]
            
            risk = metrics.get("risk_level", "low")
            risk_style = {
                "critical": "[bold red]CRITICAL[/bold red]",
                "high": "[red]HIGH[/red]",
                "medium": "[yellow]MEDIUM[/yellow]",
                "elevated": "[yellow]ELEVATED[/yellow]",
                "low": "[green]LOW[/green]"
            }.get(risk, "[green]LOW[/green]")
            
            metrics_table = Table(box=None, show_header=False, padding=(0, 1))
            metrics_table.add_column(style="cyan")
            metrics_table.add_column()
            
            metrics_table.add_row("Max Coupling:", f"{metrics.get('max_coupling', 0):.2f}")
            metrics_table.add_row("Avg Coupling:", f"{metrics.get('avg_coupling', 0):.2f}")
            metrics_table.add_row("Coupled Files:", f"{metrics.get('total_coupled_files', 0)}")
            metrics_table.add_row("Risk Level:", risk_style)
            
            modified_table = None
            if coupled_modified:
                modified_table = Table(box=box.SIMPLE, title="Modified Coupled Files")
                modified_table.add_column("File", style="blue")
                modified_table.add_column("Strength", justify="right", style="magenta")
                modified_table.add_column("Co-Changes", justify="right", style="green")
                
                for couple in coupled_modified[:5]:
                    modified_table.add_row(
                        couple["file"].split("/")[-1],
                        f"{couple['strength']:.2f}",
                        str(couple["count"])
                    )
            
            unmodified_table = None
            if coupled_unmodified:
                unmodified_table = Table(box=box.SIMPLE, title="Unmodified Coupled Files")
                unmodified_table.add_column("File", style="blue")
                unmodified_table.add_column("Strength", justify="right", style="magenta")
                unmodified_table.add_column("Co-Changes", justify="right", style="green")
                
                for couple in coupled_unmodified[:5]:
                    unmodified_table.add_row(
                        couple["file"].split("/")[-1],
                        f"{couple['strength']:.2f}",
                        str(couple["count"])
                    )
            
            content_parts = [metrics_table]
            if modified_table:
                content_parts.append("")
                content_parts.append(modified_table)
            if unmodified_table:
                content_parts.append("")
                content_parts.append(unmodified_table)
                
            file_panel = Panel(
                "\n".join(str(part) for part in content_parts),
                title=f"[blue]{filename}[/blue]",
                border_style="yellow",
                width=100
            )
            console.print(file_panel)
            console.print()
    
    def _print_impact(self, impact: Dict[str, Dict[str, Any]]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        for filename, data in impact.items():
            if "metrics" in data:
                metrics = data["metrics"]
                print(f"\nFile: {filename}")
                print(f"  Max coupling: {metrics.get('max_coupling', 0):.2f}")
                print(f"  Total coupled files: {metrics.get('total_coupled_files', 0)}")
                
                modified = data["coupled_files"]["modified"]
                unmodified = data["coupled_files"]["unmodified"]
                
                if modified:
                    print("  Modified coupled files:")
                    for couple in modified[:3]:
                        print(f"    - {couple['file']} ({couple['strength']:.2f})")
                
                if unmodified:
                    print("  Unmodified coupled files:")
                    for couple in unmodified[:3]:
                        print(f"    - {couple['file']} ({couple['strength']:.2f})")
