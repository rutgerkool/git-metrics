from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Optional, Tuple

from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text
from rich.progress_bar import ProgressBar

from gitsect.plugins.interface import MetricPlugin


class HotspotAnalysisMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Hotspot Analysis"
    
    @property
    def description(self) -> str:
        return "Identifies files with both high complexity and change frequency."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        file_changes, file_churn = self._calculate_file_metrics(commits)
        hotspots = self._calculate_hotspots(file_changes, file_churn)
        sorted_hotspots = dict(sorted(hotspots.items(), key=lambda x: x[1]["score"], reverse=True))
        return sorted_hotspots

    def _calculate_file_metrics(self, commits: List[Dict[str, Any]]) -> Tuple[DefaultDict[str, int], DefaultDict[str, int]]:
        file_changes: DefaultDict[str, int] = defaultdict(int)
        file_churn: DefaultDict[str, int] = defaultdict(int)

        for commit in commits:
            for file_change in commit["files"]:
                filename = file_change["filename"]
                additions = file_change["additions"]
                deletions = file_change["deletions"]
                churn = additions + deletions

                file_changes[filename] += 1
                file_churn[filename] += churn

        return file_changes, file_churn

    def _calculate_hotspots(self, file_changes: DefaultDict[str, int], file_churn: DefaultDict[str, int]) -> Dict[str, Dict[str, Any]]:
        hotspots: Dict[str, Dict[str, Any]] = {}
        for filename, changes in file_changes.items():
            if filename in file_churn:
                churn = file_churn[filename]
                avg_churn = churn / changes if changes > 0 else 0
                hotspot_score = changes * avg_churn
                hotspots[filename] = {
                    "changes": changes,
                    "churn": churn,
                    "avg_churn": avg_churn,
                    "score": hotspot_score
                }
        return hotspots
    
    def analyze_impact(self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        impact: Dict[str, Dict[str, Any]] = {}

        for filename, change_data in current_changes.items():
            impact[filename] = self._analyze_file_impact(filename, change_data, metric_result)

        return impact

    def _analyze_file_impact(self, filename: str, change_data: Dict[str, Any], metric_result: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        impact: Dict[str, Dict[str, Any]] = {"metrics": {}}

        if filename not in metric_result:
            impact["new_file"] = True
            return impact

        hotspot_data = metric_result[filename]
        score = hotspot_data["score"]
        current_churn = change_data["total"]

        all_scores = [h["score"] for h in metric_result.values()]
        score_percentile = sum(s <= score for s in all_scores) / len(all_scores)

        relative_change_size = current_churn / hotspot_data["avg_churn"] if hotspot_data["avg_churn"] > 0 else 0

        impact["metrics"] = {
            "hotspot_score": score,
            "score_percentile": score_percentile,
            "change_frequency": hotspot_data["changes"],
            "avg_change_size": hotspot_data["avg_churn"],
            "current_change_size": current_churn,
            "relative_change_size": relative_change_size,
            "risk_level": self._calculate_risk_level(score_percentile, relative_change_size)
        }

        return impact
    
    def _calculate_risk_level(self, percentile: float, relative_size: float) -> str:
        if percentile > 0.9 and relative_size > 1.5:
            return "critical"
        elif percentile > 0.8 or (percentile > 0.7 and relative_size > 1.5):
            return "high"
        elif percentile > 0.6 or relative_size > 2:
            return "medium"
        elif percentile > 0.4 or relative_size > 1:
            return "elevated"
        else:
            return "low"
    
    def display_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10, console: Optional[Any] = None) -> None:
        if console is None:
            self._print_result(result, limit)
        else:
            self._display_result_table(result, limit, console)
    
    def _display_result_table(self, result: Dict[str, Dict[str, Any]], limit: int, console: Any) -> None:
        max_score = max([data["score"] for data in result.values()]) if result else 0
        table = self._create_result_table(result, limit, max_score)
        console.print(table)

    def _create_result_table(self, result: Dict[str, Dict[str, Any]], limit: int, max_score: float) -> Table:
        table = Table(title="Code Hotspots Analysis", box=box.ROUNDED, title_style="bold blue", border_style="blue")
        table.add_column("Rank", justify="right", style="cyan", width=5)
        table.add_column("File", style="blue")
        table.add_column("Score", justify="right", style="magenta")
        table.add_column("Changes", justify="right", style="green")
        table.add_column("Avg Size", justify="right", style="yellow")
        table.add_column("Hotspot Level", width=30)
        
        for i, (filename, data) in enumerate(list(result.items())[:limit]):
            percentage = data["score"] / max_score if max_score > 0 else 0
            bar = ProgressBar(total=100, completed=int(percentage * 100), width=30)

            table.add_row(
                f"#{i+1}",
                filename,
                f"{data['score']:.1f}",
                str(data["changes"]),
                f"{data['avg_churn']:.1f}",
                bar
            )
        
        return table
    
    def _print_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10) -> None:
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} code hotspots:")
        
        items = list(result.items())[:limit]
        for i, (filename, data) in enumerate(items):
            print(f"{i+1}. {filename}")
            print(f"   Score: {data['score']:.1f}")
            print(f"   Changes: {data['changes']}, Churn: {data['churn']}, Avg: {data['avg_churn']:.1f}")
    
    def display_impact(self, impact: Dict[str, Dict[str, Any]], console: Optional[Any] = None) -> None:
        if console is None:
            self._print_impact(impact)
        else:
            self._display_impact_table(impact, console)

    def _display_impact_table(self, impact: Dict[str, Dict[str, Any]], console: Any) -> None:
        table = self._create_impact_table(impact)
        
        if table.rows:
            console.print(table)
        else:
            console.print(Panel("No hotspot impact data to display", border_style="yellow"))

    def _create_impact_table(self, impact: Dict[str, Dict[str, Any]]) -> Table:
        table = Table(title="Hotspot Impact Analysis", box=box.ROUNDED, title_style="bold yellow", border_style="yellow")
        table.add_column("File", style="blue")
        table.add_column("Hotspot Score", justify="right", style="magenta")  
        table.add_column("Percentile", justify="right")
        table.add_column("Avg Size", justify="right", style="cyan")
        table.add_column("Current Size", justify="right", style="green")
        table.add_column("Risk Level", justify="center")

        for filename, data in impact.items():
            self._add_impact_table_row(filename, data, table)
        
        return table

    def _add_impact_table_row(self, filename: str, data: Dict[str, Any], table: Table) -> None:
        if data.get("new_file", False):
            table.add_row(
                filename, 
                "N/A", 
                "N/A",
                "N/A",
                str(data.get("current_change_size", "N/A")),
                "[bold green]NEW FILE[/bold green]"
            )
        elif "metrics" in data:
            metrics = data["metrics"]
            score = metrics.get("hotspot_score", 0)
            percentile = metrics.get("score_percentile", 0)
            avg_size = metrics.get("avg_change_size", 0)
            current_size = metrics.get("current_change_size", 0)
            risk = metrics.get("risk_level", "low")
                
            risk_style = self._get_risk_style(risk)
                
            table.add_row(
                filename,
                f"{score:.1f}",
                f"{percentile:.1%}",
                f"{avg_size:.1f}",
                str(current_size),
                risk_style
            )

    def _get_risk_style(self, risk_level: str) -> str:
        risk_styles = {
            "critical": "[bold red]CRITICAL[/bold red]",
            "high": "[red]HIGH[/red]",
            "medium": "[yellow]MEDIUM[/yellow]",
            "elevated": "[yellow]ELEVATED[/yellow]", 
            "low": "[green]LOW[/green]"
        }
        return risk_styles.get(risk_level, "[grey]UNKNOWN[/grey]")
    
    def _print_impact(self, impact: Dict[str, Dict[str, Any]]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        for filename, data in impact.items():
            if "metrics" in data:
                metrics = data["metrics"]
                print(f"\nFile: {filename}")
                print(f"  Hotspot score: {metrics.get('hotspot_score', 0):.1f}")
                print(f"  Score percentile: {metrics.get('score_percentile', 0)*100:.1f}%")
                print(f"  Average change size: {metrics.get('avg_change_size', 0):.1f} lines")
                print(f"  Current change: {metrics.get('current_change_size', 0)} lines")
                print(f"  Risk level: {metrics.get('risk_level', 'low').upper()}")
