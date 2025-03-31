import importlib
import pkgutil
from typing import Dict, List, Optional, Type

from gitsect.plugins.interface import MetricPlugin


class PluginManager:
    def __init__(self, plugin_dir: str = "gitsect.metrics"):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Type[MetricPlugin]] = {}
        self.active_plugins: Dict[str, MetricPlugin] = {}
    
    def discover_plugins(self) -> Dict[str, Type[MetricPlugin]]:
        plugin_package = importlib.import_module(self.plugin_dir)
        plugins = self._find_plugin_classes(plugin_package)
        self.plugins = plugins
        return plugins

    def _find_plugin_classes(self, package) -> Dict[str, Type[MetricPlugin]]:
        plugins = {}
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__, f"{self.plugin_dir}."):
            if not is_pkg:
                module = importlib.import_module(name)
                plugins.update(self._get_plugin_classes(module))
        return plugins
    
    def _get_plugin_classes(self, module) -> Dict[str, Type[MetricPlugin]]:
        plugin_classes = {}
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, MetricPlugin) and attr != MetricPlugin:
                plugin_id = module.__name__.split(".")[-1]
                plugin_classes[plugin_id] = attr
        return plugin_classes

    def activate_plugins(self, plugin_ids: Optional[List[str]] = None) -> Dict[str, MetricPlugin]:
        if not self.plugins:
            self.discover_plugins()
        
        if plugin_ids is None:
            plugin_ids = list(self.plugins.keys())
        
        activated = {plugin_id: self._initialize_plugin(plugin_id) for plugin_id in plugin_ids}
        self.active_plugins = {k: v for k, v in activated.items() if v is not None}
        return self.active_plugins

    def _initialize_plugin(self, plugin_id: str) -> Optional[MetricPlugin]:
        plugin_class = self.plugins.get(plugin_id)
        if plugin_class:
            try:
                return plugin_class()
            except Exception as e:
                print(f"Failed to initialize plugin {plugin_id}: {e}")
        return None
    
    def calculate_metrics(self, commits: List[Dict[str, any]]) -> Dict[str, any]:
        return {
            plugin_id: self._calculate_plugin_metric(plugin, commits)
            for plugin_id, plugin in self.active_plugins.items()
        }

    def _calculate_plugin_metric(self, plugin: MetricPlugin, commits: List[Dict[str, any]]) -> any:
        try:
            return plugin.calculate(commits)
        except Exception as e:
            print(f"Error in {plugin.name} calculation: {e}")
            return None
    
    def analyze_impact(
        self,
        current_changes: Dict[str, Dict[str, any]],
        metric_results: Dict[str, any]
    ) -> Dict[str, any]:
        return {
            plugin_id: self._analyze_plugin_impact(plugin, current_changes, metric_results[plugin_id])
            for plugin_id, plugin in self.active_plugins.items()
            if metric_results[plugin_id] is not None
        }

    def _analyze_plugin_impact(
        self,
        plugin: MetricPlugin, 
        current_changes: Dict[str, Dict[str, any]],
        metric_result: any
    ) -> any:
        try:
            return plugin.analyze_impact(current_changes, metric_result)
        except Exception as e:
            print(f"Error in {plugin.name} impact analysis: {e}")
            return None
    
    def display_metrics(self, results: Dict[str, any], limit: int = 10, console = None) -> None:
        for plugin_id, result in results.items():
            if result is not None:
                self._display_plugin_result(self.active_plugins[plugin_id], result, limit, console)
    
    def _display_plugin_result(
        self, 
        plugin: MetricPlugin,
        result: any,
        limit: int,
        console
    ) -> None:
        try:
            plugin.display_result(result, limit, console=console)
        except Exception as e:
            print(f"Error displaying results for {plugin.name}: {e}")
    
    def display_impact(self, impact_results: Dict[str, any], console = None) -> None:
        for plugin_id, impact in impact_results.items():
            if impact is not None:
                self._display_plugin_impact(self.active_plugins[plugin_id], impact, console)
    
    def _display_plugin_impact(self, plugin: MetricPlugin, impact: any, console) -> None:
        try:
            plugin.display_impact(impact, console=console)
        except Exception as e:
            print(f"Error displaying impact for {plugin.name}: {e}")
