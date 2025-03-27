import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Any, Union, Tuple

class GitPythonCollector:
    def __init__(
        self,
        repo_path: str = ".",
        max_commits: Optional[int] = None, 
        since_days: Optional[int] = None,
        file_patterns: Optional[List[str]] = None
    ):
        self.repo_path = repo_path
        self.max_commits = max_commits
        self.since_days = since_days
        self.file_patterns = file_patterns or []
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".git_metrics_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_key(self) -> str:
        repo_abs_path = os.path.abspath(self.repo_path)
        max_commits_str = str(self.max_commits) if self.max_commits else "all"
        since_days_str = str(self.since_days) if self.since_days else "all"
        patterns_str = ",".join(self.file_patterns) if self.file_patterns else "all"
        key_str = f"{repo_abs_path}_{max_commits_str}_{since_days_str}_{patterns_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_cache_file_path(self) -> str:
        cache_key = self.get_cache_key()
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def clear_cache(self) -> None:
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    def load_from_cache(self) -> Optional[List[Dict[str, Any]]]:
        cache_file = self.get_cache_file_path()

        if os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < 86400:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)

        return None

    def save_to_cache(self, commits: List[Dict[str, Any]]) -> None:
        cache_file = self.get_cache_file_path()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(commits, f)

    def run_git_command(self, command: str) -> str:
        full_command = f"git --no-pager -C {self.repo_path} {command}"
        env = {"GIT_PAGER": "", "PYTHONIOENCODING": "utf-8", **os.environ}

        try:
            process = subprocess.run(
                full_command,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return process.stdout
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr
            raise Exception(f"Git command failed: {error_msg}") from e

    def collect_history(self) -> List[Dict[str, Any]]:
        cached_commits = self.load_from_cache()
        if cached_commits:
            return cached_commits

        all_commit_data = self.fetch_commits_batch()
        commits = self.parse_commit_data(all_commit_data)

        if self.file_patterns:
            commits = [commit for commit in commits if commit["files"]]

        self.save_to_cache(commits)
        return commits

    def fetch_commits_batch(self) -> str:
        format_str = "--pretty=format:COMMIT_START%n%H%n%an%n%ad%n%s%n%b%nCOMMIT_END"
        cmd_parts = ["log", format_str, "--name-status"]

        if self.since_days:
            since_date = datetime.datetime.now() - datetime.timedelta(days=self.since_days)
            since_str = since_date.strftime("%Y-%m-%d")
            cmd_parts.append(f'--since="{since_str}"')

        if self.max_commits:
            cmd_parts.append(f"-n {self.max_commits}")

        return self.run_git_command(" ".join(cmd_parts))

    def matches_file_pattern(self, filename: str) -> bool:
        if not self.file_patterns:
            return True

        for pattern in self.file_patterns:
            if pattern.startswith("*.") and filename.endswith(pattern[1:]):
                return True
            elif "*" in pattern:
                regex_pattern = pattern.replace(".", "\\.").replace("*", ".*")
                if re.match(regex_pattern, filename):
                    return True
            elif filename == pattern:
                return True

        return False

    def parse_commit_data(self, data: str) -> List[Dict[str, Any]]:
        raw_commits = data.split("COMMIT_START\n")[1:]

        with ProcessPoolExecutor() as executor:
            chunks = GitPythonCollector._split_list(raw_commits, os.cpu_count() or 4)
            return sum(executor.map(self._parse_commits_chunk, chunks), [])

    @staticmethod
    def _split_list(lst: List[Any], num_chunks: int) -> List[List[Any]]:
        avg = len(lst) // num_chunks
        remainder = len(lst) % num_chunks
        result = []
        start = 0

        for i in range(num_chunks):
            chunk_size = avg + (1 if i < remainder else 0)
            result.append(lst[start:start + chunk_size])
            start += chunk_size

        return result

    def _parse_commits_chunk(self, commits_chunk: List[str]) -> List[Dict[str, Any]]:
        result = []
        has_file_filters = bool(self.file_patterns)

        for commit_data in commits_chunk:
            lines = commit_data.strip().split("\n")
            if len(lines) >= 6 and lines[-1] == "COMMIT_END":
                commit_hash, author, date, message = lines[:4]
                file_changes = GitPythonCollector._parse_file_changes(lines[4:-1], self.matches_file_pattern)
                
                if not has_file_filters or file_changes:
                    result.append({
                        "hash": commit_hash,
                        "author": author,
                        "date": date,
                        "message": message,
                        "files": file_changes
                    })

        return result

    @staticmethod
    def _parse_file_changes(lines: List[str], matches_pattern: str) -> List[Dict[str, Union[str, int]]]:
        file_changes = []

        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                status, filename = parts[:2]
                if matches_pattern(filename):
                    additions = 1 if status.startswith("A") else 0
                    deletions = 1 if status.startswith("D") else 0
                    file_changes.append({
                        "filename": filename,
                        "status": status,
                        "additions": additions,
                        "deletions": deletions
                    })

        return file_changes

    def get_current_changes(self) -> Dict[str, Dict[str, Any]]:
        try:
            diff_output = self.run_git_command("diff --stat")
        except Exception as e:
            print(f"Error running git diff: {str(e)}")
            return {}

        changes = {}
        for line in diff_output.split("\n"):
            parts = line.strip().split("|")
            if len(parts) == 2:
                filename, stats_part = map(str.strip, parts)
                if self.matches_file_pattern(filename):
                    insertions, deletions = GitPythonCollector._parse_change_stats(stats_part)
                    changes[filename] = {
                        "additions": insertions,
                        "deletions": deletions,
                        "total": insertions + deletions
                    }

        return changes

    @staticmethod
    def _parse_change_stats(stats_part: str) -> Tuple[int, int]:
        stats_parts = stats_part.split()
        total_changes = int(stats_parts[0]) if stats_parts else 0

        symbols = stats_parts[1] if len(stats_parts) > 1 else ""
        insertions = symbols.count("+")
        deletions = symbols.count("-")

        if insertions == 0 and deletions == 0:
            insertions = total_changes // 2
            deletions = total_changes // 2
            if total_changes % 2 == 1:
                insertions += 1

        return insertions, deletions
