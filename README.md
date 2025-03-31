# gitsect

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
- **Impact Assessment**: Evaluate potential risks of current changes
- **Extensible Plugin System**: Add custom metrics through a plugin interface
- **High Performance**: Core operations implemented in Rust for speed
- **Interactive Visualizations**: Clear representation of complex metrics
- **File Filtering**: Analyze specific file types or patterns (e.g., only *.cs files in a C# project)

## Installation

### Prerequisites

- Python 3.8+
- Rust (latest stable)
- Git

### Setup

```bash
git clone https://github.com/yourusername/gitsect.git
cd gitsect
python build.py

```

## Usage

### Basic Commands

```bash
# Run full metrics analysis on the current repository
gitsect metrics

# Analyze only specific file types
gitsect metrics --files "*.py" "src/*"

# Analyze the potential impact of current uncommitted changes
gitsect impact

# Analyze impact for specific file types
gitsect impact --files "*.js"

# List available metric plugins
gitsect plugins
```

### Advanced Options

```bash
# Analyze a specific repository
gitsect metrics --repo /path/to/repo

# Limit the number of results displayed
gitsect metrics --limit 10

# Focus on specific metrics
gitsect metrics --metrics code_churn,developer_ownership

# Set time constraints
gitsect metrics --since-days 30 --max-commits 1000

# Force using Python implementation instead of Rust
gitsect metrics --use-python

# Clear the cache
gitsect metrics --clear-cache
```

## Extending with Custom Metrics

You can create your own metrics by implementing the `MetricPlugin` interface:

1. Create a new Python file in the `src/gitsect/metrics/` directory
2. Implement the required interface methods:
   - `name` and `description` properties
   - `calculate(commits)` method to compute the metric
   - `analyze_impact(current_changes, metric_result)` method for impact analysis
   - `display_result(result, limit)` and `display_impact(impact)` for visualization
3. Your plugin will be automatically discovered and integrated

## Architecture

The application is built using a hybrid approach:

- **Rust Core**: High-performance git operations and data collection
- **Python Frontend**: CLI interface and metric analysis
- **Plugin System**: Extensible architecture for custom metrics
