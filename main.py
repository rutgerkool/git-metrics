import argparse
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import GitMetricsCore
from plugin_manager import PluginManager

def main():
    parser = argparse.ArgumentParser(
        description='Analyze git repository using research-backed metrics',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--repo', '-r', default='.', help='Path to git repository')
    parser.add_argument('--command', '-c', choices=['metrics', 'impact', 'all'], 
                        default='all', help='Command to run')
    parser.add_argument('--limit', '-l', type=int, default=10, 
                        help='Limit for displayed items')
    parser.add_argument('--metrics', '-m', nargs='+', 
                        help='Specific metrics to analyze (omit for all)')
    parser.add_argument('--list-plugins', action='store_true', 
                        help='List available metric plugins')
    parser.add_argument('--max-commits', type=int, default=None,
                        help='Maximum number of commits to analyze (default: all)')
    parser.add_argument('--since-days', type=int, default=None,
                        help='Analyze commits from the last N days (default: all history)')
    
    args = parser.parse_args()
    
    plugin_manager = PluginManager()
    
    plugins = plugin_manager.discover_plugins()
    
    if args.list_plugins:
        print("\nAvailable metrics plugins:")
        for plugin_id, plugin_class in plugins.items():
            plugin = plugin_class()
            print(f"  {plugin_id}: {plugin.name} - {plugin.description}")
        return
    
    plugin_manager.activate_plugins(args.metrics)
    
    core = GitMetricsCore(
        args.repo,
        max_commits=args.max_commits,
        since_days=args.since_days
    )
    
    if args.command in ['metrics', 'all']:
        commits = core.collect_history()
        metrics = plugin_manager.calculate_metrics(commits)
        plugin_manager.display_metrics(metrics, args.limit)
    
    if args.command in ['impact', 'all']:
        if 'metrics' not in locals():
            commits = core.collect_history()
            metrics = plugin_manager.calculate_metrics(commits)
        
        current_changes = core.get_current_changes()
        if not current_changes:
            print("\nNo uncommitted changes found.")
        else:
            impact = plugin_manager.analyze_impact(current_changes, metrics)
            plugin_manager.display_impact(impact)

if __name__ == '__main__':
    main()
