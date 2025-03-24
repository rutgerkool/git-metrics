from collections import defaultdict
from plugin_interface import MetricPlugin

class HotspotAnalysisMetric(MetricPlugin):
    
    @property
    def name(self):
        return "Hotspot Analysis"
    
    @property
    def description(self):
        return "Identifies files with both high complexity and change frequency."
    
    def calculate(self, commits):
        file_changes = defaultdict(int)
        file_churn = defaultdict(int)
        
        for commit in commits:
            for file_change in commit['files']:
                filename = file_change['filename']
                additions = file_change['additions']
                deletions = file_change['deletions']
                churn = additions + deletions
                
                file_changes[filename] += 1
                file_churn[filename] += churn
        
        hotspots = {}
        for filename, changes in file_changes.items():
            if filename in file_churn:
                churn = file_churn[filename]
                avg_churn = churn / changes if changes > 0 else 0
                hotspot_score = changes * avg_churn
                hotspots[filename] = {
                    'changes': changes,
                    'churn': churn,
                    'avg_churn': avg_churn,
                    'score': hotspot_score
                }
        
        sorted_hotspots = dict(sorted(
            hotspots.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        ))
        
        return sorted_hotspots
    
    def analyze_impact(self, current_changes, metric_result):
        impact = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = {
                'research_backed_insights': []
            }
            
            if filename not in metric_result:
                impact[filename]['new_file'] = True
                continue
            
            hotspot_data = metric_result[filename]
            score = hotspot_data['score']
            current_churn = change_data['total']
            
            all_scores = [h['score'] for h in metric_result.values()]
            score_percentile = sum(s <= score for s in all_scores) / len(all_scores)
            
            impact[filename]['hotspot_score'] = score
            impact[filename]['score_percentile'] = score_percentile
            
            if score_percentile > 0.7:
                insight = {
                    'metric': 'Hotspot Analysis (Tornhill, 2015)',
                    'finding': f'This file is a code hotspot (top {(score_percentile*100):.0f}% of complexity and change frequency).',
                    'recommendation': 'Hotspots indicate technical debt. Consider proactive refactoring before making changes.'
                }
                impact[filename]['research_backed_insights'].append(insight)
            
            if current_churn > hotspot_data['avg_churn'] * 1.5:
                insight = {
                    'metric': 'Hotspot Analysis (Tornhill, 2015)',
                    'finding': f'Current change ({current_churn} lines) is larger than typical ({hotspot_data["avg_churn"]:.1f} lines) for this file.',
                    'recommendation': 'Large changes to hotspots increase risk. Consider breaking changes into smaller increments.'
                }
                impact[filename]['research_backed_insights'].append(insight)
        
        return impact
    
    def display_result(self, result, limit=10):
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} code hotspots:")
        
        items = list(result.items())[:limit]
        for i, (filename, data) in enumerate(items):
            print(f"{i+1}. {filename}")
            print(f"   Score: {data['score']:.1f}")
            print(f"   Changes: {data['changes']}, Churn: {data['churn']}, Avg: {data['avg_churn']:.1f}")
    
    def display_impact(self, impact):
        print(f"\n=== {self.name} Impact Analysis ===")
        
        has_insights = False
        for filename, data in impact.items():
            insights = data.get('research_backed_insights', [])
            if insights:
                has_insights = True
                print(f"\nFile: {filename}")
                for insight in insights:
                    print(f"  * {insight['finding']}")
                    print(f"    RECOMMENDATION: {insight['recommendation']}")
        
        if not has_insights:
            print("No hotspot impacts identified.\n")
