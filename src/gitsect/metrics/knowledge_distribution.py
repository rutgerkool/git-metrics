from collections import defaultdict
from typing import Dict, List, Any

from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

from gitsect.plugins.interface import MetricPlugin


class KnowledgeDistributionMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Knowledge Distribution"
    
    @property
    def description(self) -> str:
        return "Analyzes how knowledge is spread across the team."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        file_changes, author_changes, author_commit_count, file_authors = self._extract_data(commits)
        file_ownership = self._calculate_file_ownership(file_changes, author_changes, file_authors)
        all_files, all_authors = self._get_totals(file_changes, author_commit_count)
        team_knowledge = self._calculate_team_knowledge(
            all_files, all_authors, author_changes, file_ownership, author_commit_count
        )
        
        team_metrics = self._compile_team_metrics(
            team_knowledge, file_ownership, all_files, all_authors, file_authors
        )
        
        return team_metrics

    def _extract_data(self, commits):
        file_changes = defaultdict(int)
        author_changes = defaultdict(lambda: defaultdict(int))
        author_commit_count = defaultdict(int)
        file_authors = defaultdict(set)
        
        for commit in commits:
            author = commit["author"]
            author_commit_count[author] += 1
            
            for file_change in commit["files"]:
                filename = file_change["filename"]
                file_changes[filename] += 1
                author_changes[author][filename] += 1
                file_authors[filename].add(author)

        return file_changes, author_changes, author_commit_count, file_authors
    
    def _calculate_file_ownership(self, file_changes, author_changes, file_authors):
        file_ownership = {}
        for filename, authors in file_authors.items():
            if not authors:
                continue
                
            author_counts = {author: author_changes[author][filename] for author in authors}
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

        return file_ownership

    def _get_totals(self, file_changes, author_commit_count):
        all_files = set(file_changes.keys())
        all_authors = set(author_commit_count.keys())
        return all_files, all_authors

    def _calculate_team_knowledge(self, all_files, all_authors, author_changes, file_ownership, author_commit_count):
        team_knowledge = {}
        for author in all_authors:
            author_files = set(author_changes[author].keys())
            
            knowledge_coverage = len(author_files) / len(all_files) if all_files else 0
            
            knowledge_depth, touched_files = self._calculate_knowledge_depth(
                author, author_files, file_ownership
            )
            
            avg_knowledge_depth = knowledge_depth / touched_files if touched_files > 0 else 0
            
            owned_files = self._get_owned_files(author, author_files, file_ownership)
            bus_factor_contribution = len(owned_files) / len(all_files) if all_files else 0
            
            team_knowledge[author] = {
                "coverage": knowledge_coverage,
                "depth": avg_knowledge_depth,
                "owned_files": len(owned_files),
                "files_changed": len(author_files),
                "commit_count": author_commit_count[author],
                "bus_factor_contribution": bus_factor_contribution
            }

        return team_knowledge

    def _calculate_knowledge_depth(self, author, author_files, file_ownership):
        knowledge_depth = 0
        touched_files = 0
        for filename in author_files:
            if filename in file_ownership and file_ownership[filename]["dominant_author"] == author:
                knowledge_depth += file_ownership[filename]["ownership_ratio"]
                touched_files += 1

        return knowledge_depth, touched_files

    def _get_owned_files(self, author, author_files, file_ownership):
        return [
            f for f in author_files
            if f in file_ownership and file_ownership[f]["dominant_author"] == author   
        ]
    
    def _compile_team_metrics(self, team_knowledge, file_ownership, all_files, all_authors, file_authors):
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

    def _calculate_bus_factor(self, team_knowledge):
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

    def _calculate_knowledge_redundancy(self, all_files, file_authors):
        if not all_files:
            return 0
            
        total_authors = sum(len(authors) for authors in file_authors.values())
        return total_authors / len(all_files)
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        modified_files = list(current_changes.keys())
        
        team_metrics = self._compile_impact_team_metrics(metric_result)
        file_metrics = self._compile_impact_file_metrics(
            modified_files, metric_result["file_ownership"], metric_result["authors"]
        )
        
        return {
            "team_metrics": team_metrics,
            "file_metrics": file_metrics
        }
    
    def _compile_impact_team_metrics(self, metric_result):
        return {
            "bus_factor": metric_result["bus_factor"],
            "knowledge_redundancy": metric_result["knowledge_redundancy"],
            "file_count": metric_result["file_count"],
            "author_count": metric_result["author_count"],
            "risk_level": self._calculate_team_risk_level(
                metric_result["bus_factor"], metric_result["knowledge_redundancy"]
            )
        }

    def _compile_impact_file_metrics(self, modified_files, file_ownership, authors):
        file_metrics = {}
        for filename in modified_files:
            if filename not in file_ownership:
                file_metrics[filename] = {"new_file": True}
            else:
                file_metrics[filename] = {
                    "metrics": self._calculate_file_impact_metrics(filename, file_ownership, authors)
                }
        
        return file_metrics

    def _calculate_file_impact_metrics(self, filename, file_ownership, authors):
        ownership_data = file_ownership[filename]
        author_data = authors.get(ownership_data["dominant_author"], {})
        
        return {
            "dominant_author": ownership_data["dominant_author"],
            "ownership_ratio": ownership_data["ownership_ratio"], 
            "contributor_count": ownership_data["contributor_count"],
            "author_knowledge_depth": author_data.get("depth", 0),
            "author_knowledge_coverage": author_data.get("coverage", 0),
            "knowledge_risk": self._calculate_knowledge_risk(
                ownership_data["ownership_ratio"],
                ownership_data["contributor_count"],
                author_data.get("depth", 0)
            )
        }

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
       
    def display_result(self, result: Dict[str, Any], limit: int = 5, console = None):
        if console is None:
            self._print_result(result, limit)
            return
        
        self._display_team_table(result, console)
        console.print()
        self._display_knowledge_table(result, limit, console)

    def _display_team_table(self, result, console):
        team_table = self._create_team_table(result)        
        console.print(team_table)

    def _create_team_table(self, result):
        bus_factor = result["bus_factor"]
        knowledge_redundancy = result["knowledge_redundancy"]
        
        team_table = Table(
            title="Team Knowledge Distribution",
            box=box.ROUNDED,
            title_style="bold blue",
            border_style="blue"  
        )
        
        team_table.add_column("Metric", style="cyan")
        team_table.add_column("Value", style="green")
        team_table.add_column("Description", style="yellow")
        
        self._add_bus_factor_row(team_table, bus_factor)
        self._add_redundancy_row(team_table, knowledge_redundancy)
        self._add_file_count_row(team_table, result.get("file_count", 0))
        self._add_contributor_count_row(team_table, result.get("author_count", 0))

        return team_table

    def _add_bus_factor_row(self, table, bus_factor):
        bus_factor_style = self._get_bus_factor_style(bus_factor)
        table.add_row(
            "Bus Factor",
            Text(str(bus_factor), style=bus_factor_style),
            "Number of developers whose absence would risk project stalling"
        )

    def _add_redundancy_row(self, table, knowledge_redundancy):
        redundancy_style = self._get_redundancy_style(knowledge_redundancy)
        table.add_row(
            "Knowledge Redundancy",
            Text(f"{knowledge_redundancy:.2f}", style=redundancy_style),
            "Average number of developers familiar with each file"
        )

    def _add_file_count_row(self, table, file_count):
        table.add_row(
            "Files", 
            str(file_count),
            "Total files in repository"
        )

    def _add_contributor_count_row(self, table, author_count):
        table.add_row(
            "Contributors",
            str(author_count),
            "Total contributors to repository" 
        )

    def _get_bus_factor_style(self, bus_factor):
        if bus_factor <= 1:
            return "bold red"
        elif bus_factor <= 2:
            return "red"
        elif bus_factor <= 3:  
            return "yellow"
        else:
            return "green"

    def _get_redundancy_style(self, knowledge_redundancy):
        if knowledge_redundancy < 1.2:
            return "red"
        elif knowledge_redundancy < 1.5:
            return "yellow"
        else:
            return "green"
        
    def _display_knowledge_table(self, result, limit, console):
        knowledge_table = self._create_knowledge_table(result["authors"], limit)
        console.print(knowledge_table)

    def _create_knowledge_table(self, authors, limit):
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
        
        for i, (author, data) in enumerate(list(authors.items())[:limit]):
            knowledge_table.add_row(
                f"#{i+1}",
                author, 
                f"{data['coverage']*100:.1f}%",
                f"{data['depth']*100:.1f}%",  
                str(data['owned_files']),
                str(data['commit_count'])
            )

        return knowledge_table

    def _print_result(self, result, limit):
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

    def display_impact(self, impact, console = None):
        if console is None:
            self._print_impact(impact)
            return
        
        self._display_impact_team_metrics(impact["team_metrics"], console) 
        console.print()
        self._display_impact_file_metrics(impact["file_metrics"], console)

    def _display_impact_team_metrics(self, team_metrics, console):
        bus_factor = team_metrics.get("bus_factor", 0)
        risk_level = team_metrics.get("risk_level", "unknown")
        risk_style = self._get_risk_style(risk_level)
        
        team_table = Table(
            title="Team Knowledge Impact", 
            box=box.ROUNDED,
            title_style="bold yellow",
            border_style="yellow"
        )
        
        team_table.add_column("Metric", style="cyan")
        team_table.add_column("Value", style="green")
        team_table.add_row(
            "Bus Factor",
            str(bus_factor),
            risk_style  
        )
        
        team_table.add_row(
            "Knowledge Redundancy", 
            f"{team_metrics.get('knowledge_redundancy', 0):.2f}",
            ""
        )
        
        console.print(team_table)

    def _display_impact_file_metrics(self, file_metrics, console):
        if not file_metrics:
            console.print(Panel("No knowledge distribution impact data to display", border_style="yellow"))
            return
        
        file_table = self._create_impact_file_table(file_metrics)
        console.print(file_table)

    def _create_impact_file_table(self, file_metrics):
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
        
        for filename, data in file_metrics.items():
            self._add_impact_file_row(file_table, filename, data)
        
        return file_table

    def _add_impact_file_row(self, table, filename, data):
        if data.get("new_file", False):
            table.add_row(
                filename,
                "None",
                "N/A",
                "N/A", 
                Text("NEW FILE", style="bold green")
            )
        elif "metrics" in data:  
            metrics = data["metrics"]
            risk = metrics.get("knowledge_risk", "unknown")
            risk_style = self._get_risk_style(risk)
            
            table.add_row(
                filename,
                metrics.get("dominant_author", "Unknown"),
                f"{metrics.get('ownership_ratio', 0)*100:.1f}%",
                str(metrics.get("contributor_count", 0)),
                Text(risk.upper(), style=risk_style)  
            )

    def _get_risk_style(self, risk_level):
        risk_styles = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "elevated": "yellow",
            "low": "green"
        }
        return risk_styles.get(risk_level, "grey")
    
    def _print_impact(self, impact):
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
