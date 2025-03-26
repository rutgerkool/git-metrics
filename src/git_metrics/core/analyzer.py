import importlib.util
import os
import sys
from typing import Dict, List, Optional, Any

from git_metrics.core.python_git import GitPythonCollector


class GitAnalyzer:
    def __init__(
        self,
        repo_path: str = ".",
        max_commits: Optional[int] = None,
        since_days: Optional[int] = None,
        use_python: bool = False,
        file_patterns: Optional[List[str]] = None,
    ):
        self.repo_path = repo_path
        self.max_commits = max_commits
        self.since_days = since_days
        self.file_patterns = file_patterns or []
        
        self.collector = self._create_collector(repo_path, max_commits, since_days, use_python, file_patterns)
    
    def _create_collector(
        self, 
        repo_path: str,
        max_commits: Optional[int],
        since_days: Optional[int],
        use_python: bool,
        file_patterns: List[str]
    ):
        if not use_python and self._is_rust_available():
            from git_metrics import git_metrics
            return git_metrics.RustGitCollector(
                repo_path=repo_path,
                max_commits=max_commits,
                since_days=since_days,
                file_patterns=file_patterns
            )
        else:
            return GitPythonCollector(
                repo_path=repo_path,
                max_commits=max_commits,
                since_days=since_days,
                file_patterns=file_patterns
            )
    
    @staticmethod
    def _is_rust_available() -> bool:
        try:
            from git_metrics import git_metrics
            return True
        except ImportError:
            print("Rust implementation not available, using Python fallback")
            return False
    
    def collect_history(self) -> List[Dict[str, Any]]:
        return self.collector.collect_history()
    
    def get_current_changes(self) -> Dict[str, Dict[str, Any]]:
        return self.collector.get_current_changes()
    
    def clear_cache(self) -> None:
        self.collector.clear_cache()
