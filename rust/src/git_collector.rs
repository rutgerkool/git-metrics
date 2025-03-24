use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::SystemTime;
use rayon::prelude::*;

use crate::error::{GitMetricsError, Result};
use crate::models::{Commit, FileChange};

pub struct GitCollector {
    repo_path: String,
    max_commits: Option<u32>,
    since_days: Option<u32>,
    cache_dir: PathBuf,
}

impl GitCollector {
    pub fn new(repo_path: &str, max_commits: Option<u32>, since_days: Option<u32>) -> Self {
        let home_dir = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
        let cache_dir = home_dir.join(".git_metrics_cache");
        
        if !cache_dir.exists() {
            let _ = fs::create_dir_all(&cache_dir);
        }
        
        GitCollector {
            repo_path: repo_path.to_string(),
            max_commits,
            since_days,
            cache_dir,
        }
    }
    
    fn get_cache_key(&self) -> Result<String> {
        let repo_abs_path = fs::canonicalize(&self.repo_path)
            .unwrap_or_else(|_| Path::new(&self.repo_path).to_path_buf());
        
        let max_commits_str = match self.max_commits {
            Some(n) => n.to_string(),
            None => "all".to_string(),
        };
        
        let since_days_str = match self.since_days {
            Some(n) => n.to_string(),
            None => "all".to_string(),
        };
        
        let key_str = format!("{}_{}_{}", 
            repo_abs_path.display(),
            max_commits_str, 
            since_days_str
        );
        
        let digest = md5::compute(key_str.as_bytes());
        Ok(format!("{:x}", digest))
    }
    
    fn get_cache_file_path(&self) -> Result<PathBuf> {
        let cache_key = self.get_cache_key()?;
        Ok(self.cache_dir.join(format!("{}.json", cache_key)))
    }
    
    pub fn clear_cache(&self) -> Result<()> {
        if self.cache_dir.exists() {
            fs::remove_dir_all(&self.cache_dir)?;
            fs::create_dir_all(&self.cache_dir)?;
            println!("Cache cleared successfully.");
        }
        Ok(())
    }
    
    fn load_from_cache(&self) -> Result<Option<Vec<Commit>>> {
        let cache_file = self.get_cache_file_path()?;
        
        if cache_file.exists() {
            if let Ok(metadata) = fs::metadata(&cache_file) {
                if let Ok(modified) = metadata.modified() {
                    let now = SystemTime::now();
                    if let Ok(duration) = now.duration_since(modified) {
                        if duration.as_secs() < 86400 {
                            match fs::read_to_string(&cache_file) {
                                Ok(data) => {
                                    match serde_json::from_str::<Vec<Commit>>(&data) {
                                        Ok(commits) => {
                                            println!("Loading git history from cache ({} commits)...", commits.len());
                                            return Ok(Some(commits));
                                        },
                                        Err(e) => {
                                            println!("Cache file corrupted, will rebuild: {}", e);
                                        }
                                    }
                                },
                                Err(e) => {
                                    println!("Error reading cache file, will rebuild: {}", e);
                                }
                            }
                        }
                    }
                }
            }
        }
        
        Ok(None)
    }
    
    fn save_to_cache(&self, commits: &[Commit]) -> Result<()> {
        let cache_file = self.get_cache_file_path()?;
        
        let json = serde_json::to_string(commits)?;
        fs::write(&cache_file, json)?;
        println!("Saved {} commits to cache.", commits.len());
        
        Ok(())
    }
    
    fn run_git_command(&self, args: &[&str]) -> Result<String> {
        let mut cmd = Command::new("git");
        cmd.current_dir(&self.repo_path);
        cmd.arg("--no-pager");
        cmd.args(args);
        
        let output = cmd.output()
            .map_err(|e| GitMetricsError::CommandError(format!("Failed to run git command: {}", e)))?;
        
        if !output.status.success() {
            let error = String::from_utf8_lossy(&output.stderr);
            return Err(GitMetricsError::CommandError(
                format!("Git command failed: {}", error)
            ));
        }
        
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        Ok(stdout)
    }
    
    pub fn collect_history(&self) -> Result<Vec<Commit>> {
        if let Some(commits) = self.load_from_cache()? {
            return Ok(commits);
        }
        
        let _limit_msg = match (self.max_commits, self.since_days) {
            (None, None) => {
                println!("Collecting entire git history (all commits)...");
                "all".to_string()
            },
            (Some(max), Some(days)) => {
                println!("Collecting git history (limited to {} commits from the last {} days)...", max, days);
                format!("limited to {} commits from the last {} days", max, days)
            },
            (Some(max), None) => {
                println!("Collecting git history (limited to {} commits)...", max);
                format!("limited to {} commits", max)
            },
            (None, Some(days)) => {
                println!("Collecting git history (from the last {} days)...", days);
                format!("from the last {} days", days)
            },
        };
        
        let commits = self.fetch_commits_batch()?;
        println!("\nCollected {} commits", commits.len());
        
        self.save_to_cache(&commits)?;
        
        Ok(commits)
    }

    fn fetch_commits_batch(&self) -> Result<Vec<Commit>> {
        let mut command = String::from("log --pretty=format:COMMIT_START%n%H%n%an%n%ad%n%s%n%b%nCOMMIT_END --name-status");
        
        if let Some(days) = self.since_days {
            use chrono::{Utc, Duration};
            let since_date = Utc::now() - Duration::days(days as i64);
            let since_str = since_date.format("%Y-%m-%d").to_string();
            command.push_str(&format!(" --since={}", since_str));
        }
        
        if let Some(max) = self.max_commits {
            command.push_str(&format!(" -n {}", max));
        }
        
        let args: Vec<&str> = command.split_whitespace().collect();
        let output = self.run_git_command(&args)?;
        self.parse_commit_data(&output)
    }
    
    fn parse_commit_data(&self, data: &str) -> Result<Vec<Commit>> {
        let raw_commits: Vec<&str> = data.split("COMMIT_START\n").skip(1).collect();
        
        let total_commits = raw_commits.len();
        println!("Found {} commits, processing in parallel...", total_commits);
        
        let commits: Vec<Commit> = raw_commits.par_iter()
            .filter_map(|commit_data| {
                self.parse_single_commit(commit_data).ok()
            })
            .collect();
        
        Ok(commits)
    }
    
    fn parse_single_commit(&self, commit_data: &str) -> Result<Commit> {
        let lines: Vec<&str> = commit_data.lines().collect();
        
        let end_index = lines.iter().position(|&line| line == "COMMIT_END")
            .ok_or_else(|| GitMetricsError::Other("Malformed commit data: no COMMIT_END marker".to_string()))?;
        
        if lines.len() < 4 {
            return Err(GitMetricsError::Other("Not enough lines in commit data".to_string()));
        }
        
        let commit_hash = lines[0].to_string();
        let author = lines[1].to_string();
        let date = lines[2].to_string();
        let message = lines[3].to_string();
        
        let mut files = Vec::new();
        for i in 4..end_index {
            let line = lines[i].trim();
            if line.is_empty() {
                continue;
            }
            
            let parts: Vec<&str> = line.split('\t').collect();
            if parts.len() >= 2 {
                let status_str = parts[0].to_string();
                let filename = parts[1].to_string();
                
                let (additions, deletions) = if status_str.starts_with('A') {
                    (1, 0)
                } else if status_str.starts_with('D') {
                    (0, 1)
                } else {
                    (1, 1)
                };
                
                files.push(FileChange {
                    filename,
                    status: status_str,
                    additions,
                    deletions,
                });
            }
        }
        
        Ok(Commit {
            hash: commit_hash,
            author,
            date,
            message,
            files,
        })
    }
    
    pub fn get_current_changes(&self) -> Result<HashMap<String, HashMap<String, u32>>> {
        println!("Analyzing current changes...");
        
        let diff_args = vec!["diff", "--stat"];
        let diff_output = self.run_git_command(&diff_args)?;
        println!("Git diff output: {}", diff_output);
        
        let mut changes = HashMap::new();
        
        for line in diff_output.lines() {
            if line.trim().is_empty() {
                continue;
            }
            
            if !line.contains("|") {
                continue;
            }
            
            let parts: Vec<&str> = line.split("|").collect();
            if parts.len() == 2 {
                let filename = parts[0].trim().to_string();
                let stats = parts[1].trim().to_string();
                
                let mut insertions = 0;
                let mut deletions = 0;
                
                if stats.contains("insertion") {
                    let insertion_parts: Vec<&str> = stats.split("insertion").collect();
                    insertions = insertion_parts[0].trim().parse::<u32>().unwrap_or(0);
                }
                
                if stats.contains("deletion") {
                    let deletion_parts: Vec<&str> = stats.split("deletion").collect();
                    deletions = deletion_parts[0].trim().parse::<u32>().unwrap_or(0);
                }
                
                if insertions == 0 && deletions == 0 {
                    let symbols = stats.chars().collect::<Vec<char>>();
                    insertions = symbols.iter().filter(|&&c| c == '+').count() as u32;
                    deletions = symbols.iter().filter(|&&c| c == '-').count() as u32;
                    
                    if insertions == 0 && deletions == 0 {
                        if let Some(first_space) = stats.find(' ') {
                            if let Ok(total) = stats[..first_space].trim().parse::<u32>() {
                                insertions = total / 2;
                                deletions = total / 2;
                                if total % 2 == 1 {
                                    insertions += 1;
                                }
                            }
                        }
                    }
                }
                
                let mut file_changes = HashMap::new();
                file_changes.insert("additions".to_string(), insertions);
                file_changes.insert("deletions".to_string(), deletions);
                file_changes.insert("total".to_string(), insertions + deletions);
                
                changes.insert(filename, file_changes);
            }
        }
        
        println!("Analyzed {} changes", changes.len());
        Ok(changes)
    }
}
