from collections import defaultdict
from typing import Dict, List, Any

from gitsect.plugins.interface import MetricPlugin
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress_bar import ProgressBar


class CodeChurnMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Code Churn"
    
    @property 
    def description(self) -> str:
        return "Measures the amount of code added, modified, or deleted over time."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, int]:
        file_churn = defaultdict(int)
        
        for commit in commits:
            self._update_file_churn(file_churn, commit)
        
        sorted_churn = dict(sorted(file_churn.items(), key=lambda x: x[1], reverse=True))
        
        return sorted_churn

    def _update_file_churn(self, file_churn: Dict[str, int], commit: Dict[str, Any]) -> None:
        for file_change in commit["files"]:
            filename = file_change["filename"]
            churn = file_change["additions"] + file_change["deletions"] 
            file_churn[filename] += churn

    def analyze_impact(self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        impact = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = self._get_file_impact(filename, change_data, metric_result)
        
        return impact

    def _get_file_impact(self, filename: str, change_data: Dict[str, Any], metric_result: Dict[str, int]) -> Dict[str, Any]:  
        impact = {"metrics": {}}

        if filename not in metric_result:
            impact["new_file"] = True
            return impact
        
        historical_churn = metric_result[filename]
        current_churn = change_data["total"]
        churn_percentile = self._calculate_churn_percentile(filename, metric_result)
        risk_level = self._calculate_risk_level(churn_percentile, current_churn, historical_churn)

        impact["metrics"] = {
            "churn_percentile": churn_percentile,
            "historical_churn": historical_churn, 
            "current_churn": current_churn,
            "risk_level": risk_level
        }

        return impact

    def _calculate_churn_percentile(self, filename: str, metric_result: Dict[str, int]) -> float:
        all_churns = list(metric_result.values())
        historical_churn = metric_result[filename]
        return sum(c <= historical_churn for c in all_churns) / len(all_churns)

    def _calculate_risk_level(self, percentile: float, current: int, historical: int) -> str:
        if percentile > 0.9:
            return "critical"
        elif percentile > 0.8:
            return "high" 
        elif percentile > 0.6:
            return "medium"
        elif current > historical * 0.3:
            return "elevated"
        else:
            return "low"

    def display_result(self, result: Dict[str, int], limit: int = 10, console = None) -> None:
        if not console:
            self._print_result(result, limit)
            return
        
        table = self._create_churn_table(result, limit)
        console.print(table)

    def _create_churn_table(self, result: Dict[str, int], limit: int) -> Table:
        max_churn = max(result.values()) if result else 0

        table = Table(title="Code Churn Analysis", box=box.ROUNDED, title_style="bold blue", border_style="blue")
        
        table.add_column("Rank", justify="right", style="cyan", width=5)
        table.add_column("File", style="blue") 
        table.add_column("Lines Changed", justify="right", style="magenta")
        table.add_column("Relative Churn", width=30)
        
        for i, (filename, churn) in enumerate(list(result.items())[:limit]):
            percentage = churn / max_churn if max_churn > 0 else 0
            bar = ProgressBar(total=100, completed=int(percentage * 100), width=30)
            
            table.add_row(f"#{i+1}", filename, f"{churn:,}", bar)

        return table

    def _print_result(self, result: Dict[str, int], limit: int) -> None:  
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by code churn:")
        
        for i, (filename, churn) in enumerate(list(result.items())[:limit]):
            print(f"{i+1}. {filename}: {churn} lines changed")

    def display_impact(self, impact: Dict[str, Dict[str, Any]], console = None) -> None:
        if not console:
            self._print_impact(impact) 
            return
        
        self._display_impact_table(impact, console)

    def _display_impact_table(self, impact: Dict[str, Dict[str, Any]], console) -> None:
        table = Table(title="Code Churn Impact Analysis", box=box.ROUNDED, title_style="bold yellow", border_style="yellow")
        
        table.add_column("File", style="blue")
        table.add_column("Historical Churn", justify="right", style="cyan")
        table.add_column("Current Changes", justify="right", style="magenta") 
        table.add_column("Percentile", justify="right")
        table.add_column("Risk Level", justify="center")
        
        for filename, data in impact.items():
            self._add_impact_table_row(table, filename, data)

        if table.rows:
            console.print(table)
        else:
            console.print(Panel("No code churn impact data to display", border_style="yellow"))

    def _add_impact_table_row(self, table: Table, filename: str, data: Dict[str, Any]) -> None:  
        if data.get("new_file"):
            table.add_row(filename, "N/A", str(data.get("current_churn", "N/A")), "N/A", "[bold green]NEW FILE[/bold green]") 
        elif "metrics" in data:
            metrics = data["metrics"]
            historical = metrics.get("historical_churn", 0)
            current = metrics.get("current_churn", 0)
            percentile = metrics.get("churn_percentile", 0) 
            risk = metrics.get("risk_level", "low")
            risk_style = self._get_risk_style(risk)
            
            table.add_row(filename, f"{historical:,}", f"{current:,}", f"{percentile:.1%}", risk_style)

    def _get_risk_style(self, risk_level: str) -> str:
        risk_styles = {
            "critical": "[bold red]CRITICAL[/bold red]",
            "high": "[red]HIGH[/red]",
            "medium": "[yellow]MEDIUM[/yellow]", 
            "elevated": "[yellow]ELEVATED[/yellow]",
            "low": "[green]LOW[/green]"
        }
        return risk_styles.get(risk_level, "[green]LOW[/green]")

    def _print_impact(self, impact: Dict[str, Dict[str, Any]]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        for filename, data in impact.items():
            if "metrics" in data:
                metrics = data["metrics"]
                print(f"\nFile: {filename}")
                print(f"  Historical churn: {metrics.get('historical_churn', 0)} lines") 
                print(f"  Current change: {metrics.get('current_churn', 0)} lines")
                print(f"  Percentile: {metrics.get('churn_percentile', 0)*100:.1f}%")  
                print(f"  Risk level: {metrics.get('risk_level', 'low').upper()}")
