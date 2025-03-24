import subprocess
import datetime
import os
import platform
import sys
import time
import json
import hashlib
import concurrent.futures
from typing import List, Dict, Any

class GitMetricsCore:
    def __init__(self, repo_path='.', max_commits=None, since_days=None):
        self.repo_path = repo_path
        self.history_data = None
        self.max_commits = max_commits
        self.since_days = since_days
        self.cache_dir = os.path.join(os.path.expanduser('~'), '.git_metrics_cache')
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_cache_key(self) -> str:
        repo_abs_path = os.path.abspath(self.repo_path)
        
        max_commits_str = 'all' if self.max_commits is None else str(self.max_commits)
        since_days_str = 'all' if self.since_days is None else str(self.since_days)
        
        key_str = f"{repo_abs_path}_{max_commits_str}_{since_days_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cache_file_path(self) -> str:
        cache_key = self.get_cache_key()
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def load_from_cache(self) -> List[Dict[str, Any]]:
        cache_file = self.get_cache_file_path()
        
        if os.path.exists(cache_file):
            cache_mtime = os.path.getmtime(cache_file)
            cache_age = time.time() - cache_mtime
            
            if cache_age < 86400:
                try:
                    with open(cache_file, 'r') as f:
                        print(f"Loading git history from cache ({len(json.load(f))} commits)...")
                        f.seek(0)
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    print("Cache file corrupted, will rebuild...")
        
        return None
    
    def save_to_cache(self, commits: List[Dict[str, Any]]) -> None:
        cache_file = self.get_cache_file_path()
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(commits, f)
            print(f"Saved {len(commits)} commits to cache.")
        except IOError as e:
            print(f"Warning: Could not save to cache: {str(e)}")
    
    def run_git_command(self, command: str) -> str:
        full_command = f"git --no-pager -C {self.repo_path} {command}"
        
        env = os.environ.copy()
        env['GIT_PAGER'] = ''
        env['PYTHONIOENCODING'] = 'utf-8'
        
        try:
            process = subprocess.Popen(
                full_command,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False
            )
            
            stdout_bytes, stderr_bytes = process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr_bytes.decode('utf-8', errors='replace')
                raise Exception(f"Git command failed: {error_msg}")
            
            return stdout_bytes.decode('utf-8', errors='replace')
            
        except Exception as e:
            print(f"Error executing Git command: {str(e)}")
            raise
    
    def collect_history(self) -> List[Dict[str, Any]]:
        cached_commits = self.load_from_cache()
        if cached_commits is not None:
            self.history_data = cached_commits
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
        
        commit_cmd = 'log --pretty=format:%H'
        
        if self.since_days is not None:
            since_date = datetime.datetime.now() - datetime.timedelta(days=self.since_days)
            since_str = since_date.strftime("%Y-%m-%d")
            commit_cmd += f' --since="{since_str}"'
            
        if self.max_commits is not None:
            commit_cmd += f' -n {self.max_commits}'
        commit_hashes = self.run_git_command(commit_cmd).splitlines()
        
        total_commits = len(commit_hashes)
        print(f"Found {total_commits} commits in the time period, processing...")
        
        commits = self.process_commits_parallel(commit_hashes)
        
        print(f"\nCollected {len(commits)} commits")
        self.history_data = commits
        
        self.save_to_cache(commits)
        
        return commits
    
    def process_commits_parallel(self, commit_hashes: List[str]) -> List[Dict[str, Any]]:
        batch_size = 20
        num_batches = (len(commit_hashes) + batch_size - 1) // batch_size
        num_workers = min(os.cpu_count() or 4, num_batches)
        
        batches = [commit_hashes[i:i+batch_size] for i in range(0, len(commit_hashes), batch_size)]
        
        all_commits = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_batch = {executor.submit(self.process_commit_batch, batch): i 
                              for i, batch in enumerate(batches)}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_commits = future.result()
                all_commits.extend(batch_commits)
                
                completed += 1
                progress = (completed / len(batches)) * 100
                print(f"Processed {completed}/{len(batches)} batches ({progress:.1f}%)...", end='\r')
                sys.stdout.flush()
        
        return all_commits
    
    def process_commit_batch(self, commit_hashes: List[str]) -> List[Dict[str, Any]]:
        batch_commits = []
        
        for commit_hash in commit_hashes:
            try:
                commit_info = self.run_git_command(f'show --pretty=format:"%an|%ad|%s" --no-patch {commit_hash}')
                commit_info = commit_info.strip().strip('"').strip("'")
                
                if '|' in commit_info:
                    author, date, message = commit_info.split('|', 2)
                else:
                    author = "Unknown"
                    date = "Unknown"
                    message = commit_info
                
                file_changes = self.run_git_command(f'show --name-status --pretty=format: {commit_hash}')
                
                files = []
                for line in file_changes.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        status = parts[0]
                        filename = parts[1]
                        
                        if status.startswith('A'):
                            additions, deletions = 1, 0
                        elif status.startswith('D'):
                            additions, deletions = 0, 1
                        else:
                            additions, deletions = 1, 1
                        
                        files.append({
                            'filename': filename,
                            'status': status,
                            'additions': additions,
                            'deletions': deletions
                        })
                
                batch_commits.append({
                    'hash': commit_hash,
                    'author': author,
                    'date': date,
                    'message': message,
                    'files': files
                })
                
            except Exception as e:
                print(f"\nError processing commit {commit_hash}: {str(e)}")
        
        return batch_commits
    
    def get_current_changes(self) -> Dict[str, Dict[str, Any]]:
        print("Analyzing current changes...")
        
        status_output = self.run_git_command('status --porcelain')
        
        modified_files = []
        for line in status_output.split('\n'):
            if line.strip():
                status, filename = line[:2], line[3:]
                modified_files.append(filename)
        
        changes = {}
        if modified_files:
            for filename in modified_files:
                try:
                    changes[filename] = {
                        'additions': 1,
                        'deletions': 1,
                        'total': 2
                    }
                except:
                    changes[filename] = {
                        'additions': 0,
                        'deletions': 0,
                        'total': 0,
                        'error': True
                    }
        
        return changes
