from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Set

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
            "file_ownership": file_ownership
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
            "team_impact": [],
            "file_impact": {}
        }
        
        modified_files = list(current_changes.keys())
        
        bus_factor = metric_result["bus_factor"]
        if bus_factor <= 2:
            insight = {
                "metric": "Knowledge Distribution (Mockus, 2010)",
                "finding": f"Team has a low bus factor of {bus_factor}. The loss of {bus_factor} key developers " +
                         "would impact more than 50% of the codebase.",
                "recommendation": "Consider knowledge sharing sessions and pair programming to reduce key-person risk."
            }
            impact["team_impact"].append(insight)
        
        file_ownership = metric_result.get("file_ownership", {})
        
        for filename in modified_files:
            impact["file_impact"][filename] = {
                "research_backed_insights": []
            }
            
            if filename not in file_ownership:
                continue
            
            most_knowledgeable = None
            highest_ownership = 0
            
            for author, data in metric_result["authors"].items():
                author_files = data.get("owned_files", [])
                if author_files and filename in file_ownership and file_ownership[filename]["dominant_author"] == author:
                    most_knowledgeable = author
                    highest_ownership = file_ownership[filename]["ownership_ratio"]
                    break
            
            if most_knowledgeable and highest_ownership > 0.7:
                insight = {
                    "metric": "Knowledge Distribution (Mockus, 2010)",
                    "finding": f"{most_knowledgeable} has concentrated knowledge of this file ({highest_ownership*100:.0f}%).",
                    "recommendation": "Consider consulting with this developer or pair programming to ensure quality."
                }
                impact["file_impact"][filename]["research_backed_insights"].append(insight)
        
        return impact
    
    def display_result(self, result: Dict[str, Any], limit: int = 5) -> None:
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
    
    def display_impact(self, impact: Dict[str, Any]) -> None:
        print(f"\n=== {self.name} Impact Analysis ===")
        
        team_insights = impact.get("team_impact", [])
        if team_insights:
            print("\nTeam-level insights:")
            for insight in team_insights:
                print(f"  * {insight['finding']}")
                print(f"    RECOMMENDATION: {insight['recommendation']}")
        
        has_file_insights = False
        for filename, data in impact.get("file_impact", {}).items():
            insights = data.get("research_backed_insights", [])
            if insights:
                has_file_insights = True
                print(f"\nFile: {filename}")
                for insight in insights:
                    print(f"  * {insight['finding']}")
                    print(f"    RECOMMENDATION: {insight['recommendation']}")
        
        if not team_insights and not has_file_insights:
            print("No knowledge distribution impacts identified.\n")
