import importlib
import logging
import pkgutil
import sys
from typing import Dict, List, Type, Any, Optional

from git_metrics.plugins.interface import MetricPlugin


class PluginManager:
    def __init__(self, plugin_dir: str = "git_metrics.metrics"):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Type[MetricPlugin]] = {}
        self.active_plugins: Dict[str, MetricPlugin] = {}
        self.logger = logging.getLogger(__name__)
    
    def discover_plugins(self) -> Dict[str, Type[MetricPlugin]]:
        print(f"Discovering plugins in {self.plugin_dir}...")
        
        plugins = {}
        
        try:
            plugin_package = importlib.import_module(self.plugin_dir)
        except ImportError as e:
            print(f"Warning: Could not import {self.plugin_dir}: {e}")
            return plugins
        
        for _, name, is_pkg in pkgutil.iter_modules(
            plugin_package.__path__, f"{self.plugin_dir}."
        ):
            if not is_pkg:
                try:
                    module = importlib.import_module(name)
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        try:
                            if (
                                isinstance(attr, type)
                                and issubclass(attr, MetricPlugin)
                                and attr != MetricPlugin
                            ):
                                plugin_id = name.split(".")[-1]
                                plugins[plugin_id] = attr
                                print(f"  Discovered plugin: {plugin_id}")
                        except (TypeError, AttributeError):
                            continue
                except ImportError as e:
                    print(f"Warning: Failed to import plugin module {name}: {e}")
        
        self.plugins = plugins
        return plugins
    
    def activate_plugins(self, plugin_ids: Optional[List[str]] = None) -> Dict[str, MetricPlugin]:
        if not self.plugins:
            self.discover_plugins()
        
        if plugin_ids is None:
            plugin_ids = list(self.plugins.keys())
        
        activated = {}
        for plugin_id in plugin_ids:
            if plugin_id in self.plugins:
                plugin_class = self.plugins[plugin_id]
                try:
                    activated[plugin_id] = plugin_class()
                    print(f"  Activated plugin: {plugin_id}")
                except Exception as e:
                    print(f"Warning: Failed to initialize plugin {plugin_id}: {e}")
            else:
                print(f"Warning: Plugin {plugin_id} not found")
        
        self.active_plugins = activated
        return activated
    
    def calculate_metrics(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = {}
        for plugin_id, plugin in self.active_plugins.items():
            print(f"Calculating {plugin.name}...")
            try:
                results[plugin_id] = plugin.calculate(commits)
            except Exception as e:
                print(f"Error in {plugin.name} calculation: {e}")
                results[plugin_id] = None
        
        return results
    
    def analyze_impact(
        self, current_changes: Dict[str, Dict[str, Any]], metric_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        impact_results = {}
        for plugin_id, plugin in self.active_plugins.items():
            if plugin_id in metric_results and metric_results[plugin_id] is not None:
                print(f"Analyzing impact using {plugin.name}...")
                try:
                    impact_results[plugin_id] = plugin.analyze_impact(
                        current_changes, metric_results[plugin_id]
                    )
                except Exception as e:
                    print(f"Error in {plugin.name} impact analysis: {e}")
        
        return impact_results
    
    def display_metrics(self, results: Dict[str, Any], limit: int = 10) -> None:
        for plugin_id, result in results.items():
            if plugin_id in self.active_plugins and result is not None:
                plugin = self.active_plugins[plugin_id]
                try:
                    plugin.display_result(result, limit)
                except Exception as e:
                    print(f"Error displaying results for {plugin.name}: {e}")
    
    def display_impact(self, impact_results: Dict[str, Any]) -> None:
        print("\n=== Impact analysis of current changes ===")
        
        for plugin_id, impact in impact_results.items():
            if plugin_id in self.active_plugins and impact is not None:
                plugin = self.active_plugins[plugin_id]
                try:
                    plugin.display_impact(impact)
                except Exception as e:
                    print(f"Error displaying impact for {plugin.name}: {e}")
