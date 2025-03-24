from collections import defaultdict
from plugin_interface import MetricPlugin

class DeveloperOwnershipMetric(MetricPlugin):
    
    @property
    def name(self):
        return "Developer Ownership"
    
    @property
    def description(self):
        return "Measures the concentration of changes among developers."
    
    def calculate(self, commits):
        author_changes = defaultdict(lambda: defaultdict(int))
        file_authors = defaultdict(set)
        
        for commit in commits:
            author = commit['author']
            
            for file_change in commit['files']:
                filename = file_change['filename']
                author_changes[filename][author] += 1
                file_authors[filename].add(author)
        
        file_ownership = {}
        for filename, authors in file_authors.items():
            if not authors:
                continue
                
            author_counts = {}
            for author in authors:
                author_counts[author] = author_changes[filename][author]
            
            total_changes = sum(author_counts.values())
            if total_changes == 0:
                continue
                
            dominant_author = max(author_counts.items(), key=lambda x: x[1])
            ownership = dominant_author[1] / total_changes
            
            file_ownership[filename] = {
                'dominant_author': dominant_author[0],
                'ownership_ratio': ownership,
                'contributor_count': len(authors),
                'author_changes': author_counts,
                'total_changes': total_changes
            }
        
        sorted_ownership = dict(sorted(
            file_ownership.items(),
            key=lambda x: x[1]['ownership_ratio'],
            reverse=True
        ))
        
        return sorted_ownership
    
    def analyze_impact(self, current_changes, metric_result):
        impact = {}
        
        for filename, change_data in current_changes.items():
            impact[filename] = {
                'research_backed_insights': []
            }
            
            if filename not in metric_result:
                impact[filename]['new_file'] = True
                continue
            
            ownership_data = metric_result[filename]
            dominant_author = ownership_data['dominant_author']
            ownership_ratio = ownership_data['ownership_ratio']
            contributor_count = ownership_data['contributor_count']
            
            impact[filename]['ownership'] = {
                'dominant_author': dominant_author,
                'ownership_ratio': ownership_ratio,
                'contributor_count': contributor_count
            }
            
            if ownership_ratio > 0.8:
                insight = {
                    'metric': 'Developer Ownership (Bird et al., 2011)',
                    'finding': f'Strong ownership: {dominant_author} has made {(ownership_ratio*100):.0f}% of changes.',
                    'recommendation': 'Consider knowledge sharing to reduce key-person risk, while maintaining clear ownership.'
                }
                impact[filename]['research_backed_insights'].append(insight)
            elif ownership_ratio < 0.3:
                insight = {
                    'metric': 'Developer Ownership (Bird et al., 2011)',
                    'finding': f'Weak ownership: Most active contributor ({dominant_author}) has only made ' +
                              f'{(ownership_ratio*100):.0f}% of changes across {contributor_count} contributors.',
                    'recommendation': 'Weak ownership correlates with more defects. Consider consolidating ownership.'
                }
                impact[filename]['research_backed_insights'].append(insight)
        
        return impact
    
    def display_result(self, result, limit=10):
        print(f"\n=== {self.name} ===")
        print(f"\nTop {limit} files by ownership strength:")
        
        items = list(result.items())[:limit]
        for i, (filename, data) in enumerate(items):
            print(f"{i+1}. {filename}")
            print(f"   Owner: {data['dominant_author']} ({data['ownership_ratio']*100:.1f}%)")
            print(f"   Contributors: {data['contributor_count']}")
    
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
            print("No ownership impacts identified.\n")
