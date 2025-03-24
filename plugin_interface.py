from abc import ABC, abstractmethod

class MetricPlugin(ABC):

    @property
    @abstractmethod
    def name(self):
        """Return the name of the metric."""
        pass
    
    @property
    @abstractmethod
    def description(self):
        """Return a description of the metric."""
        pass
    
    @abstractmethod
    def calculate(self, commits):
        """
        Calculate the metric from history data.
        
        Args:
            commits: List of commit data from GitMetricsCore
            
        Returns:
            The calculated metric result
        """
        pass
    
    @abstractmethod
    def analyze_impact(self, current_changes, metric_result):
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
    def display_result(self, result, limit=10):
        """
        Display the metric result in a human-readable format.
        
        Args:
            result: The metric result from calculate()
            limit: Maximum number of items to display
        """
        pass
    
    @abstractmethod
    def display_impact(self, impact):
        """
        Display the impact analysis in a human-readable format.
        
        Args:
            impact: The impact analysis from analyze_impact()
        """
        pass
