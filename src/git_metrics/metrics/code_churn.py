from collections import defaultdict
from git_metrics.plugins.interface import MetricPlugin
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from typing import Optional, Any

class CodeChurnMetric(MetricPlugin):
    
    @property
    def name(self):
        return "Code Churn"
    
    @property
    def description(self):
        return "Measures the amount of code added, modified, or deleted over time."
    
    def calculate(self, commits):
        file_churn = defaultdict(int)
        
        for commit in commits:
            for file_change in commit['files']:
                filename = file_change['filename']
                additions = file_change['additions']
                deletions = file_change['deletions']
                churn = additions + deletions
                
                file_churn[filename] += churn
        
        sorted_churn = dict(sorted(
            file_churn.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        return sorted_churn
    
    def analyze_impact(self, current_changes, metric_result):
        impact = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = {
                'metrics': {}
            }
            
            if filename not in metric_result:
                impact[filename]['new_file'] = True
                continue
            
            historical_churn = metric_result[filename]
            current_churn = change_data['total']
            
            all_churns = list(metric_result.values())
            churn_percentile = sum(c <= historical_churn for c in all_churns) / len(all_churns)
            
            impact[filename]['metrics'] = {
                'churn_percentile': churn_percentile,
                'historical_churn': historical_churn,
                'current_churn': current_churn,
                'risk_level': self._calculate_risk_level(churn_percentile, current_churn, historical_churn)
            }
        
        return impact
    
    def _calculate_risk_level(self, percentile, current, historical):
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
    
    def display_result(self, result, limit=10, console=None):
        if console is None:
            self._print_result(result, limit)
            return
        
        max_churn = max(result.values()) if result else 0
        
        table = Table(
            title=f"Code Churn Analysis", 
            box=box.ROUNDED, 
            title_style="bold blue", 
            border_style="blue"
        )
        
        table.add_column("Rank", justify="right", style="cyan", width=5)
        table.add_column("File", style="blue")
        table.add_column("Lines Changed", justify="right", style="magenta")
        table.add_column("Relative Churn", width=30)
        
        for i, (filename, churn) in enumerate(list(result.items())[:limit]):
            percentage = churn / max_churn
            
            bar = ProgressBar(total=100, completed=int(percentage * 100), width=30)
            
            table.add_row(
                f"#{i+1}",
                filename,
                f"{churn:,}",
                bar
            )
        
        console.print(table)
    
    def _print_result(self, result, limit=10):
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by code churn:")
        
        items = list(result.items())[:limit]
        for i, (filename, churn) in enumerate(items):
            print(f"{i+1}. {filename}: {churn} lines changed")
    
    def display_impact(self, impact, console=None):
        if console is None:
            self._print_impact(impact)
            return
        
        table = Table(
            title=f"Code Churn Impact Analysis", 
            box=box.ROUNDED, 
            title_style="bold yellow", 
            border_style="yellow"
        )
        
        table.add_column("File", style="blue")
        table.add_column("Historical Churn", justify="right", style="cyan")
        table.add_column("Current Changes", justify="right", style="magenta")
        table.add_column("Percentile", justify="right")
        table.add_column("Risk Level", justify="center")
        
        has_entries = False
        for filename, data in impact.items():
            if data.get('new_file', False):
                table.add_row(
                    filename,
                    "N/A",
                    str(data.get('current_churn', 'N/A')),
                    "N/A",
                    "[bold green]NEW FILE[/bold green]"
                )
                has_entries = True
            elif 'metrics' in data:
                metrics = data['metrics']
                historical = metrics.get('historical_churn', 0)
                current = metrics.get('current_churn', 0)
                percentile = metrics.get('churn_percentile', 0)
                risk = metrics.get('risk_level', 'low')
                
                risk_style = {
                    "critical": "[bold red]CRITICAL[/bold red]",
                    "high": "[red]HIGH[/red]",
                    "medium": "[yellow]MEDIUM[/yellow]",
                    "elevated": "[yellow]ELEVATED[/yellow]",
                    "low": "[green]LOW[/green]"
                }.get(risk, "[green]LOW[/green]")
                
                table.add_row(
                    filename,
                    f"{historical:,}",
                    f"{current:,}",
                    f"{percentile:.1%}",
                    risk_style
                )
                has_entries = True
        
        if has_entries:
            console.print(table)
        else:
            console.print(Panel("No code churn impact data to display", border_style="yellow"))
    
    def _print_impact(self, impact):
        print(f"\n=== {self.name} Impact Analysis ===")
        
        for filename, data in impact.items():
            if 'metrics' in data:
                metrics = data['metrics']
                print(f"\nFile: {filename}")
                print(f"  Historical churn: {metrics.get('historical_churn', 0)} lines")
                print(f"  Current change: {metrics.get('current_churn', 0)} lines")
                print(f"  Percentile: {metrics.get('churn_percentile', 0)*100:.1f}%")
                print(f"  Risk level: {metrics.get('risk_level', 'low').upper()}")
