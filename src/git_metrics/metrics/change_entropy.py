import math
from collections import defaultdict
from typing import Dict, List, Any, DefaultDict, Set

from git_metrics.plugins.interface import MetricPlugin


class ChangeEntropyMetric(MetricPlugin):
    @property
    def name(self) -> str:
        return "Change Entropy"
    
    @property
    def description(self) -> str:
        return "Measures the complexity and distribution of changes."
    
    def calculate(self, commits: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        author_changes: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        file_authors: DefaultDict[str, Set[str]] = defaultdict(set)
        
        for commit in commits:
            author = commit["author"]
            
            for file_change in commit["files"]:
                filename = file_change["filename"]
                author_changes[filename][author] += 1
                file_authors[filename].add(author)
        
        file_entropy: Dict[str, Dict[str, Any]] = {}
        for filename, authors in file_authors.items():
            author_contributions: Dict[str, int] = {}
            for author in authors:
                author_contributions[author] = author_changes[filename][author]
            
            total = sum(author_contributions.values())
            if total == 0:
                continue
                
            entropy = 0
            for count in author_contributions.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log2(p)
            
            author_count = len(author_contributions)
            max_entropy = math.log2(author_count) if author_count > 0 else 0
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
            
            file_entropy[filename] = {
                "entropy": normalized_entropy,
                "contributors": author_count,
                "total_changes": total
            }
        
        sorted_entropy = dict(sorted(
            file_entropy.items(),
            key=lambda x: x[1]["entropy"],
            reverse=True
        ))
        
        return sorted_entropy
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_result: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        impact: Dict[str, Dict[str, Any]] = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = {
                "research_backed_insights": []
            }
            
            if filename not in metric_result:
                impact[filename]["new_file"] = True
                continue
            
            entropy_data = metric_result[filename]
            entropy = entropy_data["entropy"]
            contributors = entropy_data["contributors"]
            
            impact[filename]["change_entropy"] = entropy
            impact[filename]["contributors"] = contributors
            
            if entropy > 0.8 and contributors > 3:
                insight = {
                    "metric": "Change Entropy (Hassan, 2009)",
                    "finding": f"High change entropy ({entropy:.2f}): {contributors} different developers " +
                              f"have modified this file with no clear ownership pattern.",
                    "recommendation": "High entropy files need careful code review as they correlate with defects. " +
                                     "Consider establishing clearer ownership."
                }
                impact[filename]["research_backed_insights"].append(insight)
            elif entropy < 0.3 and contributors > 1:
                insight = {
                    "metric": "Change Entropy (Hassan, 2009)",
                    "finding": f"Low change entropy ({entropy:.2f}) despite {contributors} contributors " +
                              f"indicates dominant ownership with occasional contributions.",
                    "recommendation": "Low entropy typically indicates healthier code; maintain this pattern."
                }
                impact[filename]["research_backed_insights"].append(insight)
        
        return impact
    
    def display_result(self, result: Dict[str, Dict[str, Any]], limit: int = 10) -> None:
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by change entropy:")
        
        items = list(result.items())[:limit]
        for i, (filename, data) in enumerate(items):
            print(f"{i+1}. {filename}")
            print(f"   Entropy: {data['entropy']:.2f}")
            print(f"   Contributors: {data['contributors']}")
            print(f"   Total Changes: {data['total_changes']}")
    
    def display_impact(self, impact: Dict[str, Dict[str, Any]]) -> None:
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
