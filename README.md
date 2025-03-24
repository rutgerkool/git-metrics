# Git Commit Analyzer

A tool for analyzing Git repositories to improve productivity and code quality through research-backed metrics.

## Overview

This project extracts metrics from Git history and provides actionable insights to improve code quality, reduce technical debt, and optimize development workflows. It uses a hybrid Python/Rust architecture for performance and extensibility.

## Research-Backed Metrics

The tool implements metrics based on established software engineering research:

1. **Code Churn** (Nagappan & Ball, 2005)  
   Measures the frequency and size of code changes to identify unstable components.

2. **Change Coupling** (D'Ambros et al., 2009)  
   Identifies files that frequently change together, suggesting architectural dependencies.

3. **Developer Ownership** (Bird et al., 2011)  
   Analyzes code ownership patterns and their impact on code quality.

4. **Hotspot Analysis** (Tornhill, 2015)  
   Detects high-risk files with both high complexity and frequent changes.

5. **Change Entropy** (Hassan, 2009)  
   Measures the distribution and complexity of changes across files.

6. **Knowledge Distribution** (Mockus, 2010)  
   Evaluates team-wide knowledge distribution and "bus factor" risks.

## Features

- **Repository Analysis**: Comprehensive metrics to identify code quality issues
- **Impact Assessment**: Evaluate potential risks of current uncommitted changes
- **Extensible Plugin System**: Add custom metrics through a clean plugin interface
- **High Performance**: Core operations implemented in Rust for speed
- **Interactive Visualizations**: Clear representation of complex metrics
- **CLI Interface**: Integrate with your existing workflows and tools

## Installation

### Prerequisites

- Python 3.8+
- Rust (latest stable)
- Git

### Setup

```bash
git clone https://github.com/yourusername/git-metrics.git
cd git-metrics
python build.py

```

## Usage

### Basic Commands

```bash
# Run full metrics analysis on the current repository
git-metrics metrics

# Analyze the potential impact of current uncommitted changes
git-metrics impact

# List available metric plugins
git-metrics plugins
```

### Advanced Options

```bash
# Analyze a specific repository
git-metrics metrics --repo /path/to/repo

# Limit the number of results displayed
git-metrics metrics --limit 10

# Focus on specific metrics
git-metrics metrics --metrics code_churn,developer_ownership

# Set time constraints
git-metrics metrics --since-days 30 --max-commits 1000

# Force using Python implementation instead of Rust
git-metrics metrics --use-python

# Clear the cache for fresh analysis
git-metrics metrics --clear-cache

# Verbose output for debugging
git-metrics metrics --verbose
```

## Extending with Custom Metrics

You can create your own metrics by implementing the `MetricPlugin` interface:

1. Create a new Python file in the `src/git_metrics/metrics/` directory
2. Implement the required interface methods:
   - `name` and `description` properties
   - `calculate(commits)` method to compute the metric
   - `analyze_impact(current_changes, metric_result)` method for impact analysis
   - `display_result(result, limit)` and `display_impact(impact)` for visualization
3. Your plugin will be automatically discovered and integrated

## Architecture

The application is built using a hybrid approach:

- **Rust Core**: High-performance git operations and data collection
- **Python Frontend**: Flexible CLI interface and metric analysis
- **Plugin System**: Extensible architecture for custom metrics
