from collections import defaultdict
from plugin_interface import MetricPlugin

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
                'research_backed_insights': []
            }
            
            if filename not in metric_result:
                impact[filename]['new_file'] = True
                continue
            
            historical_churn = metric_result[filename]
            current_churn = change_data['total']
            
            all_churns = list(metric_result.values())
            churn_percentile = sum(c <= historical_churn for c in all_churns) / len(all_churns)
            
            impact[filename]['churn_percentile'] = churn_percentile
            impact[filename]['historical_churn'] = historical_churn
            impact[filename]['current_churn'] = current_churn
            
            if churn_percentile > 0.8:
                insight = {
                    'metric': 'Code Churn (Nagappan & Ball, 2005)',
                    'finding': f'This file is in the top {(churn_percentile*100):.0f}% of churn. ' +
                              f'Historical churn: {historical_churn} lines. Current change: {current_churn} lines.',
                    'recommendation': 'High-churn files correlate with defects. Consider refactoring to improve stability.'
                }
                impact[filename]['research_backed_insights'].append(insight)
            elif current_churn > historical_churn * 0.3:
                insight = {
                    'metric': 'Code Churn (Nagappan & Ball, 2005)',
                    'finding': f'Current change ({current_churn} lines) is significant compared to historical churn ' +
                              f'({historical_churn} lines).',
                    'recommendation': 'Large changes increase defect probability. Consider breaking into smaller changes.'
                }
                impact[filename]['research_backed_insights'].append(insight)
        
        return impact
    
    def display_result(self, result, limit=10):
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by code churn:")
        
        items = list(result.items())[:limit]
        for i, (filename, churn) in enumerate(items):
            print(f"{i+1}. {filename}: {churn} lines changed")
    
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
            print("No code churn impacts identified.\n")
