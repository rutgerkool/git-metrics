import os
import importlib
import pkgutil
from typing import Dict, List, Type

from plugin_interface import MetricPlugin

class PluginManager:

    def __init__(self, plugin_dir='metrics'):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Type[MetricPlugin]] = {}
        self.active_plugins: Dict[str, MetricPlugin] = {}
    
    def discover_plugins(self):
        print(f"Discovering plugins in {self.plugin_dir}...")
        
        package_name = self.plugin_dir
        try:
            plugin_package = importlib.import_module(package_name)
        except ImportError:
            print(f"Warning: Could not import {package_name}")
            return {}
        
        plugins = {}
        for _, name, is_pkg in pkgutil.iter_modules(plugin_package.__path__, f"{package_name}."):
            if not is_pkg:
                try:
                    module = importlib.import_module(name)
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        try:
                            if (isinstance(attr, type) and 
                                issubclass(attr, MetricPlugin) and 
                                attr != MetricPlugin):
                                
                                plugin_id = name.split('.')[-1]
                                plugins[plugin_id] = attr
                        except (TypeError, AttributeError):
                            continue
                except ImportError as e:
                    print(f"Warning: Failed to import plugin module {name}: {e}")
        
        self.plugins = plugins
        return plugins
    
    def activate_plugins(self, plugin_ids=None):
        if not self.plugins:
            self.discover_plugins()
        
        if plugin_ids is None:
            plugin_ids = list(self.plugins.keys())
        
        activated = {}
        for plugin_id in plugin_ids:
            if plugin_id in self.plugins:
                plugin_class = self.plugins[plugin_id]
                activated[plugin_id] = plugin_class()
            else:
                print(f"Warning: Plugin {plugin_id} not found")
        
        self.active_plugins = activated
        return activated
    
    def calculate_metrics(self, commits):
        results = {}
        for plugin_id, plugin in self.active_plugins.items():
            print(f"Calculating {plugin.name}...")
            results[plugin_id] = plugin.calculate(commits)
        
        return results
    
    def analyze_impact(self, current_changes, metric_results):
        impact_results = {}
        for plugin_id, plugin in self.active_plugins.items():
            if plugin_id in metric_results:
                print(f"Analyzing impact using {plugin.name}...")
                impact_results[plugin_id] = plugin.analyze_impact(
                    current_changes, 
                    metric_results[plugin_id]
                )
        
        return impact_results
    
    def display_metrics(self, results, limit=10):
        for plugin_id, result in results.items():
            plugin = self.active_plugins[plugin_id]
            plugin.display_result(result, limit)
    
    def display_impact(self, impact_results):
        print("\n=== Impact analysis of current changes ===")
        
        for plugin_id, impact in impact_results.items():
            plugin = self.active_plugins[plugin_id]
            plugin.display_impact(impact)
