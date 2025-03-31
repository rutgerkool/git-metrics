use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, SystemTime};
use chrono::{Utc, TimeZone};
use log::{debug, info};
use rayon::prelude::*;
use regex::Regex;

use crate::error::{GitMetricsError, Result};
use crate::models::{Commit, FileChange};

const CACHE_TTL_SECONDS: u64 = 86400;
const COMMIT_START_MARKER: &str = "COMMIT_START\n";
const COMMIT_END_MARKER: &str = "COMMIT_END";

pub struct GitCollector {
    repo_path: String,
    max_commits: Option<u32>,
    since_days: Option<u32>,
    cache_dir: PathBuf,
    file_patterns: Vec<String>,
}

impl GitCollector {
    pub fn new(
        repo_path: &str, 
        max_commits: Option<u32>, 
        since_days: Option<u32>,
        file_patterns: Vec<String>
    ) -> Self {
        let home_dir = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
        let cache_dir = home_dir.join(".gitsect_cache");
        
        if !cache_dir.exists() {
            let _ = fs::create_dir_all(&cache_dir);
        }
        
        GitCollector {
            repo_path: repo_path.to_string(),
            max_commits,
            since_days,
            cache_dir,
            file_patterns,
        }
    }
    
    fn get_cache_key(&self) -> Result<String> {
        let repo_abs_path = fs::canonicalize(&self.repo_path)
            .unwrap_or_else(|_| Path::new(&self.repo_path).to_path_buf());
        
        let max_commits_str = self.max_commits
            .map_or_else(|| "all".to_string(), |n| n.to_string());
        
        let since_days_str = self.since_days
            .map_or_else(|| "all".to_string(), |n| n.to_string());
        
        let patterns_str = if self.file_patterns.is_empty() {
            "all".to_string()
        } else {
            self.file_patterns.join(",")
        };
        
        let key_str = format!("{}_{}_{}_{}",
            repo_abs_path.display(),
            max_commits_str, 
            since_days_str,
            patterns_str
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
            fs::remove_dir_all(&self.cache_dir)
                .map_err(|e| GitMetricsError::IoError(e))?;
            fs::create_dir_all(&self.cache_dir)
                .map_err(|e| GitMetricsError::IoError(e))?;
            info!("Cache cleared successfully.");
        }
        Ok(())
    }
    
    fn load_from_cache(&self) -> Result<Option<Vec<Commit>>> {
        let cache_file = self.get_cache_file_path()?;
        
        if !cache_file.exists() {
            debug!("Cache file doesn't exist");
            return Ok(None);
        }

        let metadata = fs::metadata(&cache_file)
            .map_err(|e| GitMetricsError::IoError(e))?;
        
        let modified = metadata.modified()
            .map_err(|e| GitMetricsError::IoError(e))?;
        
        let now = SystemTime::now();
        let duration = now.duration_since(modified)
            .map_err(|_| GitMetricsError::Other("Cache file modification time is in the future".to_string()))?;
        
        if duration > Duration::from_secs(CACHE_TTL_SECONDS) {
            debug!("Cache file too old (> 24h)");
            return Ok(None);
        }

        let data = fs::read_to_string(&cache_file)
            .map_err(|e| GitMetricsError::IoError(e))?;
        
        match serde_json::from_str::<Vec<Commit>>(&data) {
            Ok(commits) => {
                info!("Loading git history from cache ({} commits)...", commits.len());
                Ok(Some(commits))
            },
            Err(e) => {
                debug!("Cache file corrupted, will rebuild: {}", e);
                Ok(None)
            }
        }
    }
    
    fn save_to_cache(&self, commits: &[Commit]) -> Result<()> {
        let cache_file = self.get_cache_file_path()?;
        
        let json = serde_json::to_string(commits)
            .map_err(|e| GitMetricsError::SerializationError(e))?;
        
        fs::write(&cache_file, json)
            .map_err(|e| GitMetricsError::IoError(e))?;
        
        info!("Saved {} commits to cache.", commits.len());
        
        Ok(())
    }
    
    fn run_git_command(&self, args: &[&str]) -> Result<String> {
        let mut cmd = Command::new("git");
        cmd.current_dir(&self.repo_path);
        cmd.arg("--no-pager");
        cmd.args(args);
        
        debug!("Running git command: git --no-pager {}", args.join(" "));
        
        let output = cmd.output()
            .map_err(|e| GitMetricsError::Other(format!("Failed to execute git command: {}", e)))?;
        
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
        
        self.log_collection_start();
        
        let commits = self.fetch_commits_batch()?;
        info!("\nCollected {} commits", commits.len());
        
        self.save_to_cache(&commits)?;
        
        Ok(commits)
    }
    
    fn log_collection_start(&self) {
        let pattern_str = if self.file_patterns.is_empty() {
            "all files".to_string()
        } else {
            format!("files matching: {}", self.file_patterns.join(", "))
        };
        
        match (self.max_commits, self.since_days) {
            (None, None) => {
                info!("Collecting entire git history ({})...", pattern_str);
            },
            (Some(max), Some(days)) => {
                info!("Collecting git history (limited to {} commits from the last {} days, {})...", 
                      max, days, pattern_str);
            },
            (Some(max), None) => {
                info!("Collecting git history (limited to {} commits, {})...", 
                      max, pattern_str);
            },
            (None, Some(days)) => {
                info!("Collecting git history (from the last {} days, {})...", 
                      days, pattern_str);
            },
        };
    }

    fn fetch_commits_batch(&self) -> Result<Vec<Commit>> {
        let base_args = [
            "log",
            "--pretty=format:COMMIT_START%n%H%n%an%n%ad%n%s%n%b%nCOMMIT_END",
            "--name-status"
        ];
        
        let owned_strings = self.build_commit_args();
        let mut all_args = Vec::with_capacity(base_args.len() + owned_strings.len());
        all_args.extend_from_slice(&base_args);
        
        for owned in &owned_strings {
            all_args.push(owned.as_str());
        }
        
        let output = self.run_git_command(&all_args)?;
        self.parse_commit_data(&output)
    }
    
    fn build_commit_args(&self) -> Vec<String> {
        let mut args = Vec::new();
        
        if let Some(days) = self.since_days {
            let since_date = Utc::now()
                .checked_sub_signed(chrono::Duration::days(days as i64))
                .unwrap_or_else(|| Utc.with_ymd_and_hms(2000, 1, 1, 0, 0, 0).unwrap());
            
            args.push(format!("--since={}", since_date.format("%Y-%m-%d")));
        }
        
        if let Some(max) = self.max_commits {
            args.push(format!("-n {}", max));
        }
        
        args
    }
    
    fn parse_commit_data(&self, data: &str) -> Result<Vec<Commit>> {
        let raw_commits: Vec<&str> = data.split(COMMIT_START_MARKER).skip(1).collect();
        let total_commits = raw_commits.len();
        info!("Found {} commits, processing in parallel...", total_commits);
        
        let has_file_filters = !self.file_patterns.is_empty();
        
        let commits: Vec<Commit> = raw_commits.par_iter()
            .filter_map(|commit_data| {
                self.parse_single_commit(commit_data).ok()
            })
            .filter(|commit| {
                !has_file_filters || !commit.files.is_empty()
            })
            .collect();
        
        Ok(commits)
    }
    
    fn matches_file_pattern(&self, filename: &str) -> bool {
        if self.file_patterns.is_empty() {
            return true;
        }
        
        for pattern in &self.file_patterns {
            if pattern.starts_with("*.") && filename.ends_with(&pattern[1..]) {
                return true;
            }
            else if pattern.contains('*') {
                let regex_pattern = pattern
                    .replace(".", "\\.")
                    .replace("*", ".*");
                
                if let Ok(regex) = Regex::new(&regex_pattern) {
                    if regex.is_match(filename) {
                        return true;
                    }
                }
            }
            else if filename == pattern {
                return true;
            }
        }
        
        false
    }
    
    fn parse_single_commit(&self, commit_data: &str) -> Result<Commit> {
        let lines: Vec<&str> = commit_data.lines().collect();
        
        let end_index = lines.iter()
            .position(|&line| line == COMMIT_END_MARKER)
            .ok_or_else(|| GitMetricsError::Other(
                "Malformed commit data: no COMMIT_END marker".to_string()
            ))?;
        
        if lines.len() < 4 {
            return Err(GitMetricsError::Other(
                "Not enough lines in commit data".to_string()
            ));
        }
        
        let commit_hash = lines[0].to_string();
        let author = lines[1].to_string();
        let date = lines[2].to_string();
        let message = lines[3].to_string();
        
        let files = self.parse_file_changes(&lines[4..end_index])?;
        
        Ok(Commit {
            hash: commit_hash,
            author,
            date,
            message,
            files,
        })
    }
    
    fn parse_file_changes(&self, file_lines: &[&str]) -> Result<Vec<FileChange>> {
        let mut files = Vec::new();
        
        for line in file_lines {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            
            let parts: Vec<&str> = line.split('\t').collect();
            if parts.len() < 2 {
                continue;
            }
            
            let status_str = parts[0].to_string();
            let filename = parts[1].to_string();
            
            if !self.matches_file_pattern(&filename) {
                continue;
            }
            
            let (additions, deletions) = self.status_to_change_count(&status_str);
            
            files.push(FileChange {
                filename,
                status: status_str,
                additions,
                deletions,
            });
        }
        
        Ok(files)
    }
    
    fn status_to_change_count(&self, status: &str) -> (u32, u32) {
        match status.chars().next() {
            Some('A') => (1, 0),
            Some('D') => (0, 1),
            Some('M') | Some('R') | Some('C') => (1, 1),
            _ => (0, 0),
        }
    }
    
    pub fn get_current_changes(&self) -> Result<HashMap<String, HashMap<String, u32>>> {
        info!("Analyzing current changes...");
        
        let diff_output = self.run_git_command(&["diff", "--stat"])?;
        debug!("Git diff output: {}", diff_output);
        
        let mut changes = HashMap::new();
        
        for line in diff_output.lines() {
            if let Some(file_changes) = self.parse_diff_line(line) {
                changes.insert(file_changes.0, file_changes.1);
            }
        }
        
        info!("Analyzed {} changes", changes.len());
        Ok(changes)
    }
    
    fn parse_diff_line(&self, line: &str) -> Option<(String, HashMap<String, u32>)> {
        let line = line.trim();
        if line.is_empty() || !line.contains('|') {
            return None;
        }
        
        let parts: Vec<&str> = line.split('|').collect();
        if parts.len() != 2 {
            return None;
        }
        
        let filename = parts[0].trim().to_string();
        
        if !self.matches_file_pattern(&filename) {
            return None;
        }
        
        let stats = parts[1].trim();
        let (insertions, deletions) = self.parse_diff_stats(stats);
        
        let mut file_changes = HashMap::new();
        file_changes.insert("additions".to_string(), insertions);
        file_changes.insert("deletions".to_string(), deletions);
        file_changes.insert("total".to_string(), insertions + deletions);
        
        Some((filename, file_changes))
    }
    
    fn parse_diff_stats(&self, stats: &str) -> (u32, u32) {
        let mut insertions = 0;
        let mut deletions = 0;
        
        if stats.contains("insertion") {
            if let Some(n) = stats.split_whitespace()
                .next()
                .and_then(|s| s.parse::<u32>().ok()) {
                insertions = n;
            }
        }
        
        if stats.contains("deletion") {
            if let Some(n) = stats.split("deletion")
                .next()
                .and_then(|s| s.trim().split_whitespace().next())
                .and_then(|s| s.parse::<u32>().ok()) {
                deletions = n;
            }
        }
        
        if insertions == 0 && deletions == 0 {
            insertions = stats.chars().filter(|&c| c == '+').count() as u32;
            deletions = stats.chars().filter(|&c| c == '-').count() as u32;
        }
        
        if insertions == 0 && deletions == 0 {
            if let Some(total) = stats.split_whitespace()
                .next()
                .and_then(|s| s.parse::<u32>().ok()) {
                
                insertions = total / 2;
                deletions = total / 2;
                if total % 2 == 1 {
                    insertions += 1;
                }
            }
        }
        
        (insertions, deletions)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    
    #[test]
    fn test_status_to_change_count() {
        let collector = GitCollector::new(".", None, None, Vec::new());
        
        assert_eq!(collector.status_to_change_count("A"), (1, 0));
        assert_eq!(collector.status_to_change_count("D"), (0, 1));
        assert_eq!(collector.status_to_change_count("M"), (1, 1));
        assert_eq!(collector.status_to_change_count("R100"), (1, 1));
        assert_eq!(collector.status_to_change_count("??"), (0, 0));
    }
    
    #[test]
    fn test_matches_file_pattern() {
        let patterns = vec![
            "*.rs".to_string(),
            "src/*".to_string(),
            "exact_file.txt".to_string()
        ];
        
        let collector = GitCollector::new(".", None, None, patterns);
        
        assert!(collector.matches_file_pattern("main.rs"));
        assert!(collector.matches_file_pattern("src/lib.rs"));
        assert!(collector.matches_file_pattern("exact_file.txt"));
        
        assert!(!collector.matches_file_pattern("main.js"));
        assert!(!collector.matches_file_pattern("test/main.rs"));
        assert!(!collector.matches_file_pattern("exact_file_2.txt"));
    }
    
    #[test]
    fn test_parse_diff_stats() {
        let collector = GitCollector::new(".", None, None, Vec::new());
        
        assert_eq!(collector.parse_diff_stats("5 insertions(+), 3 deletions(-)"), (5, 3));
        assert_eq!(collector.parse_diff_stats("2 insertions(+)"), (2, 0));
        assert_eq!(collector.parse_diff_stats("7 deletions(-)"), (0, 7));
        assert_eq!(collector.parse_diff_stats("++--"), (2, 2));
        assert_eq!(collector.parse_diff_stats("10 "), (5, 5));
        assert_eq!(collector.parse_diff_stats("11 "), (6, 5));
    }
    
    #[test]
    fn test_get_cache_key() {
        let dir = tempdir().unwrap();
        let repo_path = dir.path().to_str().unwrap();
        
        let collector1 = GitCollector::new(repo_path, Some(10), None, Vec::new());
        let collector2 = GitCollector::new(repo_path, Some(10), None, Vec::new());
        let collector3 = GitCollector::new(repo_path, Some(20), None, Vec::new());
        
        let key1 = collector1.get_cache_key().unwrap();
        let key2 = collector2.get_cache_key().unwrap();
        let key3 = collector3.get_cache_key().unwrap();
        
        assert_eq!(key1, key2);
        assert_ne!(key1, key3);
    }
}
