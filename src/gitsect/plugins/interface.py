from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class MetricPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the name of the metric.
        
        Returns:
            Human-readable name of the metric
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Return a description of the metric.
        
        Returns:
            Human-readable description of the metric
        """
        pass
    
    @abstractmethod
    def calculate(self, commits: List[Dict[str, Any]]) -> Any:
        """
        Calculate the metric from history data.
        
        Args:
            commits: List of commit data from GitAnalyzer
            
        Returns:
            The calculated metric result (type varies by metric)
        """
        pass
    
    @abstractmethod
    def analyze_impact(self, current_changes: Dict[str, Dict[str, Any]], metric_result: Any) -> Any:
        """
        Analyze the impact of current changes on this metric.
        
        Args:
            current_changes: Dict of current uncommitted changes
            metric_result: Previously calculated metric result
            
        Returns:
            Dict of impact analysis for each file
        """
        pass
    
    @abstractmethod
    def display_result(self, result: Any, limit: int = 10, console: Optional[Any] = None) -> None:
        """
        Display the metric result in a human-readable format.
        
        Args:
            result: The metric result from calculate()
            limit: Maximum number of items to display
            console: Rich console object for enhanced display (if None, use print)
        """
        pass
    
    @abstractmethod
    def display_impact(self, impact: Any, console: Optional[Any] = None) -> None:
        """
        Display the impact analysis in a human-readable format.
        
        Args:
            impact: The impact analysis from analyze_impact()
            console: Rich console object for enhanced display (if None, use print)
        """
        pass
