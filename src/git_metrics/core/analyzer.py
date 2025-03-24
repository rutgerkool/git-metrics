import importlib.util
import os
import sys
from typing import Dict, List, Optional, Any

try:
    from git_metrics import git_metrics
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("Rust implementation not available, using Python fallback")

from git_metrics.core.python_git import GitPythonCollector


class GitAnalyzer:
    def __init__(
        self,
        repo_path: str = ".",
        max_commits: Optional[int] = None,
        since_days: Optional[int] = None,
        use_python: bool = False,
    ):
        self.repo_path = repo_path
        self.max_commits = max_commits
        self.since_days = since_days
        self.use_python = use_python
        
        if RUST_AVAILABLE and not use_python:
            self.collector = git_metrics.RustGitCollector(
                repo_path=repo_path,
                max_commits=max_commits,
                since_days=since_days
            )
            print("Using Rust implementation for Git operations")
        else:
            self.collector = GitPythonCollector(
                repo_path=repo_path,
                max_commits=max_commits,
                since_days=since_days
            )
            print("Using Python implementation for Git operations")
    
    def collect_history(self) -> List[Dict[str, Any]]:
        return self.collector.collect_history()
    
    def get_current_changes(self) -> Dict[str, Dict[str, Any]]:
        return self.collector.get_current_changes()
    
    def clear_cache(self) -> None:
        self.collector.clear_cache()
