import math
from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Set, Optional
from rich import box
from rich.panel import Panel
from rich.table import Table
from gitsect.plugins.interface import MetricPlugin

class ChangeEntropyMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Change Entropy"
    
    @property
    def description(self) -> str:
        return "Measures the complexity and distribution of changes."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        author_changes, file_authors = self._extract_author_data(commits)
        file_entropy = self._calculate_file_entropy(author_changes, file_authors)
        sorted_entropy = self._sort_entropy_results(file_entropy)
        
        return sorted_entropy

    def _extract_author_data(self, commits: List[Dict[str, Any]]) -> tuple:
        author_changes = defaultdict(lambda: defaultdict(int))
        file_authors = defaultdict(set)

        for commit in commits:
            author = commit["author"]
            for file_change in commit["files"]:
                filename = file_change["filename"]
                author_changes[filename][author] += 1
                file_authors[filename].add(author)

        return author_changes, file_authors

    def _calculate_file_entropy(self, author_changes, file_authors) -> Dict[str, Dict[str, Any]]:
        file_entropy = {}
        for filename, authors in file_authors.items():
            author_contributions = {author: author_changes[filename][author] for author in authors}
            
            total = sum(author_contributions.values())
            if total == 0:
                continue
                
            entropy = self._calculate_entropy(author_contributions.values(), total)
            
            author_count = len(author_contributions)
            max_entropy = math.log2(author_count) if author_count > 0 else 0
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
            
            file_entropy[filename] = {
                "entropy": normalized_entropy,
                "contributors": author_count,
                "total_changes": total
            }

        return file_entropy

    def _calculate_entropy(self, contributions: List[int], total: int) -> float:
        entropy = 0
        for count in contributions:
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def _sort_entropy_results(self, file_entropy: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return dict(sorted(
            file_entropy.items(),
            key=lambda x: x[1]["entropy"],
            reverse=True
        ))
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        impact = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = self._analyze_file_impact(filename, metric_result)
        
        return impact

    def _analyze_file_impact(self, filename: str, metric_result: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        impact = {"research_backed_insights": []}
            
        if filename not in metric_result:
            impact["new_file"] = True
            return impact
            
        entropy_data = metric_result[filename]
        entropy = entropy_data["entropy"]
        contributors = entropy_data["contributors"]
        
        impact["change_entropy"] = entropy
        impact["contributors"] = contributors
            
        insights = self._generate_insights(entropy, contributors)
        impact["research_backed_insights"].extend(insights)

        return impact

    def _generate_insights(self, entropy: float, contributors: int) -> List[Dict[str, str]]:
        insights = []

        if entropy > 0.8 and contributors > 3:
            insights.append({
                "metric": "Change Entropy (Hassan, 2009)",
                "finding": f"High change entropy ({entropy:.2f}): {contributors} different developers " +
                          f"have modified this file with no clear ownership pattern.",
                "recommendation": "High entropy files need careful code review as they correlate with defects. " +
                                 "Consider establishing clearer ownership."
            })
        elif entropy < 0.3 and contributors > 1:
            insights.append({
                "metric": "Change Entropy (Hassan, 2009)",
                "finding": f"Low change entropy ({entropy:.2f}) despite {contributors} contributors " +
                          f"indicates dominant ownership with occasional contributions.",
                "recommendation": "Low entropy typically indicates healthier code; maintain this pattern."
            })

        return insights
    
    def display_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10, console: Optional[Any] = None) -> None:
        if console is None:
            self._print_result(result, limit)
            return
            
        table = self._create_entropy_table(result, limit)
        console.print(table)
    
    def _create_entropy_table(self, result: Dict[str, Dict[str, Any]], limit) -> Table:    
        table = Table(
            title="Change Entropy Analysis",
            box=box.ROUNDED,
            title_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Rank", justify="right", style="cyan", width=5)
        table.add_column("File", style="blue")
        table.add_column("Entropy", justify="right", style="magenta")
        table.add_column("Contributors", justify="right", style="yellow")
        table.add_column("Changes", justify="right")
        
        for i, (filename, data) in enumerate(list(result.items())[:limit]):
            table.add_row(
                f"#{i+1}",
                filename,
                f"{data['entropy']:.2f}",
                str(data['contributors']),
                str(data['total_changes'])
            )
        
        return table

    def _print_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10) -> None:
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by change entropy:")
        
        for i, (filename, data) in enumerate(list(result.items())[:limit]):
            print(f"{i+1}. {filename}")
            print(f"   Entropy: {data['entropy']:.2f}")
            print(f"   Contributors: {data['contributors']}")
            print(f"   Total Changes: {data['total_changes']}")
    
    def display_impact(self, impact: Dict[str, Dict[str, Any]], console: Optional[Any] = None) -> None:
        if console is None:
            self._print_impact(impact)
            return
            
        self._display_impact_panel(impact, console)

    def _display_impact_panel(self, impact: Dict[str, Dict[str, Any]], console: Any) -> None: 
        has_insights = False
        insights_text = []
        
        for filename, data in impact.items():
            insights = data.get("research_backed_insights", [])
            if insights:
                has_insights = True
                insights_text.append(f"[bold blue]{filename}[/bold blue]")
                for insight in insights:
                    insights_text.append(f"  * {insight['finding']}")
                    insights_text.append(f"    [green]RECOMMENDATION:[/green] {insight['recommendation']}")
                insights_text.append("")
        
        if has_insights:
            console.print(Panel("\n".join(insights_text), title="Change Entropy Impact Analysis", border_style="yellow"))
        else:
            console.print(Panel("No entropy impacts identified.", title="Change Entropy Impact Analysis", border_style="yellow"))
    
    def _print_impact(self, impact: Dict[str, Dict[str, Any]]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        has_insights = False
        for filename, data in impact.items():
            insights = data.get("research_backed_insights", [])
            if insights:
                has_insights = True
                print(f"\nFile: {filename}")
                for insight in insights:
                    print(f"  * {insight['finding']}")
                    print(f"    RECOMMENDATION: {insight['recommendation']}")
        
        if not has_insights:
            print("No entropy impacts identified.\n")
