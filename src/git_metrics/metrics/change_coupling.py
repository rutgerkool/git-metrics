from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Any, Tuple, DefaultDict, Set

import networkx as nx

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
                "research_backed_insights": [],
                "coupled_files_modified": [],
                "coupled_files_unmodified": []
            }
            
            if filename not in metric_result["file_changes"]:
                impact[filename]["new_file"] = True
                continue
            
            for pair, data in coupling_data.items():
                if filename in pair:
                    other_file = pair[0] if pair[1] == filename else pair[1]
                    coupling_strength = data["jaccard"]
                    
                    if other_file in modified_files:
                        impact[filename]["coupled_files_modified"].append({
                            "file": other_file,
                            "strength": coupling_strength
                        })
                    else:
                        impact[filename]["coupled_files_unmodified"].append({
                            "file": other_file,
                            "strength": coupling_strength
                        })
            
            impact[filename]["coupled_files_modified"].sort(key=lambda x: x["strength"], reverse=True)
            impact[filename]["coupled_files_unmodified"].sort(key=lambda x: x["strength"], reverse=True)
            
            strong_unmodified = [f for f in impact[filename]["coupled_files_unmodified"] if f["strength"] > 0.7]
            if strong_unmodified:
                top_coupled = strong_unmodified[:3]
                files_str = ", ".join([f"{f['file']} ({f['strength']:.2f})" for f in top_coupled])
                
                insight = {
                    "metric": "Change Coupling (D'Ambros et al., 2009)",
                    "finding": f"These files are frequently changed with {filename} but are NOT in your current changes: {files_str}",
                    "recommendation": "Consider if these files also need changes to maintain consistency."
                }
                impact[filename]["research_backed_insights"].append(insight)
        
        return impact
    
    def display_result(self, result: Dict[str, Any], limit: int = 10) -> None:
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} strongest file couplings:")
        
        items = list(result["coupling"].items())[:limit]
        for i, (pair, data) in enumerate(items):
            print(f"{i+1}. {pair[0]} ↔ {pair[1]}: {data['jaccard']:.2f}")
            print(f"   Co-changed {data['count']} times")
    
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
            print("No coupling impacts identified.\n")
