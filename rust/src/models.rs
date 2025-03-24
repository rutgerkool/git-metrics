use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct FileChange {
    pub filename: String,
    pub status: String,
    pub additions: u32,
    pub deletions: u32,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Commit {
    pub hash: String,
    pub author: String,
    pub date: String,
    pub message: String,
    pub files: Vec<FileChange>,
}
