import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Any, Optional, Tuple


class GitPythonCollector:
    def __init__(
        self,
        repo_path: str = ".",
        max_commits: Optional[int] = None,
        since_days: Optional[int] = None,
    ):
        self.repo_path = repo_path
        self.max_commits = max_commits
        self.since_days = since_days
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".git_metrics_cache")
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_cache_key(self) -> str:
        repo_abs_path = os.path.abspath(self.repo_path)
        
        max_commits_str = "all" if self.max_commits is None else str(self.max_commits)
        since_days_str = "all" if self.since_days is None else str(self.since_days)
        
        key_str = f"{repo_abs_path}_{max_commits_str}_{since_days_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cache_file_path(self) -> str:
        cache_key = self.get_cache_key()
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def clear_cache(self) -> None:
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir)
    
    def load_from_cache(self) -> Optional[List[Dict[str, Any]]]:
        cache_file = self.get_cache_file_path()
        
        if os.path.exists(cache_file):
            cache_mtime = os.path.getmtime(cache_file)
            cache_age = time.time() - cache_mtime
            
            if cache_age < 86400:
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        commits = json.load(f)
                        print(f"Loading git history from cache ({len(commits)} commits)...")
                        return commits
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Cache file corrupted, will rebuild: {e}")
        
        return None
    
    def save_to_cache(self, commits: List[Dict[str, Any]]) -> None:
        cache_file = self.get_cache_file_path()
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(commits, f)
            print(f"Saved {len(commits)} commits to cache.")
        except IOError as e:
            print(f"Warning: Could not save to cache: {str(e)}")
    
    def run_git_command(self, command: str) -> str:
        full_command = f"git --no-pager -C {self.repo_path} {command}"
        
        env = os.environ.copy()
        env["GIT_PAGER"] = ""
        env["PYTHONIOENCODING"] = "utf-8"
        
        try:
            process = subprocess.Popen(
                full_command,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False,
            )
            
            stdout_bytes, stderr_bytes = process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr_bytes.decode("utf-8", errors="replace")
                raise Exception(f"Git command failed: {error_msg}")
            
            return stdout_bytes.decode("utf-8", errors="replace")
            
        except Exception as e:
            print(f"Error executing Git command: {str(e)}")
            raise
    
    def collect_history(self) -> List[Dict[str, Any]]:
        cached_commits = self.load_from_cache()
        if cached_commits is not None:
            return cached_commits
        
        if self.max_commits is None and self.since_days is None:
            print("Collecting entire git history (all commits)...")
            limit_msg = "all"
        else:
            limit_parts = []
            if self.max_commits is not None:
                limit_parts.append(f"limited to {self.max_commits} commits")
            if self.since_days is not None:
                limit_parts.append(f"from the last {self.since_days} days")
            limit_msg = " ".join(limit_parts)
            print(f"Collecting git history ({limit_msg})...")
        
        all_commit_data = self.fetch_commits_batch()
        commits = self.parse_commit_data(all_commit_data)
        
        print(f"\nCollected {len(commits)} commits")
        
        self.save_to_cache(commits)
        
        return commits
    
    def fetch_commits_batch(self) -> str:
        format_str = "--pretty=format:COMMIT_START%n%H%n%an%n%ad%n%s%n%b%nCOMMIT_END"
        
        cmd_parts = ["log", format_str, "--name-status"]
        
        if self.since_days is not None:
            since_date = datetime.datetime.now() - datetime.timedelta(days=self.since_days)
            since_str = since_date.strftime("%Y-%m-%d")
            cmd_parts.append(f'--since="{since_str}"')
            
        if self.max_commits is not None:
            cmd_parts.append(f"-n {self.max_commits}")
            
        return self.run_git_command(" ".join(cmd_parts))
    
    def parse_commit_data(self, data: str) -> List[Dict[str, Any]]:
        commits = []
        
        raw_commits = data.split("COMMIT_START\n")[1:]
        
        total_commits = len(raw_commits)
        print(f"Found {total_commits} commits, processing...")
        
        with ProcessPoolExecutor() as executor:
            cpu_count = os.cpu_count() or 4
            chunks = self._split_list(raw_commits, cpu_count)
            futures = [executor.submit(self._parse_commits_chunk, chunk) for chunk in chunks]
            
            commits = []
            completed = 0
            for future in ProcessPoolExecutor().map(self._parse_commits_chunk, chunks):
                commits.extend(future)
                
                completed += 1
                progress = (completed / len(chunks)) * 100
                print(f"Processed {completed}/{len(chunks)} chunks ({progress:.1f}%)...", end="\r")
        
        return commits
    
    def _split_list(self, lst: List[Any], num_chunks: int) -> List[List[Any]]:
        avg = len(lst) // num_chunks
        remainder = len(lst) % num_chunks
        
        result = []
        i = 0
        for _ in range(num_chunks):
            chunk_size = avg + 1 if remainder > 0 else avg
            remainder -= 1 if remainder > 0 else 0
            result.append(lst[i:i+chunk_size])
            i += chunk_size
            
        return result
    
    def _parse_commits_chunk(self, commits_chunk: List[str]) -> List[Dict[str, Any]]:
        result = []
        
        for commit_data in commits_chunk:
            lines = commit_data.split("\n")
            
            if not lines or "COMMIT_END" not in lines:
                continue
                
            end_index = lines.index("COMMIT_END")
            
            if len(lines) >= 4:
                commit_hash = lines[0]
                author = lines[1]
                date = lines[2]
                message = lines[3]
                
                files = []
                for i in range(4, end_index):
                    line = lines[i].strip()
                    if not line:
                        continue
                    
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        status = parts[0]
                        filename = parts[1]
                        
                        if status.startswith("A"):
                            additions, deletions = 1, 0
                        elif status.startswith("D"):
                            additions, deletions = 0, 1
                        else:
                            additions, deletions = 1, 1
                        
                        files.append({
                            "filename": filename,
                            "status": status,
                            "additions": additions,
                            "deletions": deletions
                        })
                
                result.append({
                    "hash": commit_hash,
                    "author": author,
                    "date": date,
                    "message": message,
                    "files": files
                })
        
        return result
    
    def get_current_changes(self) -> Dict[str, Dict[str, Any]]:
        print("Analyzing current changes...")

        try:
            diff_output = self.run_git_command("diff --stat")
            print(f"Git diff output: {diff_output}")
        except Exception as e:
            print(f"Error running git diff: {str(e)}")
            return {}

        changes = {}
        for line in diff_output.split("\n"):
            if not line.strip():
                continue
                
            if "file changed" in line or "files changed" in line:
                continue
                
            try:
                parts = line.split("|")
                if len(parts) == 2:
                    filename = parts[0].strip()
                    stats_part = parts[1].strip()

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
                    
                    changes[filename] = {
                        "additions": insertions,
                        "deletions": deletions,
                        "total": total_changes
                    }
            except Exception as e:
                print(f"Error processing line '{line}': {str(e)}")
                if "filename" in locals():
                    changes[filename] = {
                        "additions": 0,
                        "deletions": 0,
                        "total": 0,
                        "error": True
                    }

        print(f"Analyzed {len(changes)} changes")
        return changes
