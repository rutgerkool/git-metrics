use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3::exceptions::PyRuntimeError;

mod git_collector;
mod error;
mod models;

use crate::git_collector::GitCollector;
use crate::models::Commit;

#[pymodule]
fn gitsect(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustGitCollector>()?;
    Ok(())
}

#[pyclass(name = "RustGitCollector")]
struct RustGitCollector {
    repo_path: String,
    max_commits: Option<u32>,
    since_days: Option<u32>,
    file_patterns: Vec<String>,
}

#[pymethods]
impl RustGitCollector {
    #[new]
    #[pyo3(signature = (repo_path = ".", max_commits = None, since_days = None, file_patterns = None))]
    fn new(
        repo_path: &str, 
        max_commits: Option<u32>, 
        since_days: Option<u32>,
        file_patterns: Option<Vec<String>>
    ) -> Self {
        RustGitCollector {
            repo_path: repo_path.to_string(),
            max_commits,
            since_days,
            file_patterns: file_patterns.unwrap_or_else(Vec::new),
        }
    }

    fn collect_history(&self, py: Python) -> PyResult<PyObject> {
        let collector = GitCollector::new(
            &self.repo_path, 
            self.max_commits, 
            self.since_days,
            self.file_patterns.clone()
        );
        
        match collector.collect_history() {
            Ok(commits) => {
                let result = PyList::empty(py);
                for commit in commits {
                    let commit_dict = commit_to_py_dict(py, &commit)?;
                    result.append(commit_dict)?;
                }
                Ok(result.into())
            },
            Err(err) => {
                Err(PyRuntimeError::new_err(format!("Failed to collect history: {}", err)))
            }
        }
    }

    fn get_current_changes(&self, py: Python) -> PyResult<PyObject> {
        let collector = GitCollector::new(
            &self.repo_path, 
            None, 
            None,
            self.file_patterns.clone()
        );
        
        match collector.get_current_changes() {
            Ok(changes) => {
                let result = PyDict::new(py);
                
                for (file, change_data) in changes {
                    let data_dict = PyDict::new(py);
                    
                    for (key, value) in change_data {
                        data_dict.set_item(key, value)?;
                    }
                    
                    result.set_item(file, data_dict)?;
                }
                
                Ok(result.into())
            },
            Err(err) => {
                Err(PyRuntimeError::new_err(format!("Failed to get current changes: {}", err)))
            }
        }
    }

    fn clear_cache(&self) -> PyResult<()> {
        let collector = GitCollector::new(&self.repo_path, None, None, Vec::new());
        collector.clear_cache().map_err(|err| {
            PyRuntimeError::new_err(format!("Failed to clear cache: {}", err))
        })
    }
}

fn commit_to_py_dict(py: Python, commit: &Commit) -> PyResult<PyObject> {
    let commit_dict = PyDict::new(py);
    
    commit_dict.set_item("hash", &commit.hash)?;
    commit_dict.set_item("author", &commit.author)?;
    commit_dict.set_item("date", &commit.date)?;
    commit_dict.set_item("message", &commit.message)?;
    
    let files = PyList::empty(py);
    for file in &commit.files {
        let file_dict = PyDict::new(py);
        file_dict.set_item("filename", &file.filename)?;
        file_dict.set_item("status", &file.status)?;
        file_dict.set_item("additions", file.additions)?;
        file_dict.set_item("deletions", file.deletions)?;
        files.append(file_dict)?;
    }
    
    commit_dict.set_item("files", files)?;
    
    Ok(commit_dict.into())
}
