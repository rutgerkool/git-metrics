use thiserror::Error;

#[derive(Error, Debug)]
pub enum GitMetricsError {
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Command error: {0}")]
    CommandError(String),
    
    #[error("{0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, GitMetricsError>;
