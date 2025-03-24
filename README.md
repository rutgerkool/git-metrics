# Git Commit Analyzer

A tool for analyzing Git repositories to improve productivity and code quality.

## Overview

This project extracts metrics from your Git history and provides insights based on these metrics.

## Research-Backed Metrics

The tool implements different metrics based on the following research:

   1. **Code Churn** (Nagappan & Ball, 2005)  
   2. **Change Coupling** (D'Ambros et al., 2009)  
   3. **Developer Ownership** (Bird et al., 2011)  
   4. **Hotspot Analysis** (Tornhill, 2015)  
   5. **Change Entropy** (Hassan, 2009)  
   6. **Knowledge Distribution** (Mockus, 2010)  

## Features

- Analyze metrics per repository to identify code quality issues
- Assess the impact of current uncommitted changes
- Provide a plugin interface to allow for metric extensions

## Installation

```bash
git clone https://github.com/yourusername/git-metrics.git
cd git-metrics
python -m pip install -r .\requirements.txt
```

## Usage

### Basic Usage

```bash
# Run full analysis
python main.py

# Show repository metrics
python main.py --command metrics

# Analyze impact of current changes
python main.py --command impact
```

### Advanced Options

```bash
# Analyze a specific repository
python main.py --repo /path/to/repo

# Limit the number of results displayed
python main.py --limit 5

# Use only specific metrics
python main.py --metrics code_churn developer_ownership

# List available plugins
python main.py --list-plugins
```

## Adding Custom Metrics

You can extend the tool with your own metrics by creating a new plugin:

1. Create a new file in the `metrics/` directory (e.g., `metrics/my_metric.py`)
2. Implement the `MetricPlugin` interface
3. The metric will be automatically integrated
