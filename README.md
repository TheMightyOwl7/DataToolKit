# Data Processing Toolkit

A comprehensive desktop application for financial data processing, built with Python and DuckDB. The toolkit provides an intuitive GUI for common data operations like reconciliation, cleaning, aggregation, and analysis.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Tools Overview](#tools-overview)
  - [Reconcile Files](#1-reconcile-files)
  - [Clean Data](#2-clean-data)
  - [Aggregate Data](#3-aggregate-data)
  - [Analyze Data](#4-analyze-data)
- [Project Structure](#project-structure)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)

---

## Features

- **High Performance**: Uses DuckDB for blazing-fast processing of large CSV files (100k+ rows)
- **User-Friendly GUI**: Built with Tkinter for a native desktop experience
- **Multi-Tool Suite**: Four specialized tools for different data operations
- **Auto-Detection**: Intelligent column type detection for dates, amounts, and descriptions
- **Export Ready**: Export results to CSV with one click
- **No Database Setup**: In-memory processing with zero configuration

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Steps

1. **Clone or download the repository**:
   ```bash
   git clone https://github.com/yourusername/DataToolKit.git
   cd DataToolKit
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Getting Started

Launch the application from the project root directory:

```bash
python src/main.py
```

The home screen will display all available tools. Click on any tool card to open it.

> **Tip**: You can also run `py main.py` from inside the `src/` directory.

---

## Tools Overview

### 1. Reconcile Files

**Purpose**: Compare and match records between two CSV files (e.g., bank statement vs. accounting ledger).

#### How to Use

1. Select **Source A** and **Source B** CSV files
2. The tool will auto-detect date, amount, and description columns
3. Choose a **Match Key** (a column that exists in both files)
4. Set an optional **Amount Tolerance** for fuzzy matching
5. Click **Run Reconciliation**

#### Results Categories

| Category | Description |
|----------|-------------|
| **Exact Matches** | Records that match perfectly on key, date, and amount |
| **Date Notes** | Key and amount match, but dates differ |
| **Amount Variances** | Key matches, but amount differs beyond tolerance |
| **Missing in B** | Records in Source A not found in Source B |
| **Missing in A** | Records in Source B not found in Source A |

#### Features

- File preview with first 3 rows
- Auto-clean amounts (removes `$`, `,`, handles `(negative)`)
- Date format normalization (handles `DD/MM/YYYY`, `MM/DD/YYYY`, ISO)
- Right-click to copy cell values
- Export individual tabs or all results

---

### 2. Clean Data

**Purpose**: Standardize data formats and types before further processing or import.

#### How to Use

1. Select an input CSV file
2. Review auto-detected column types
3. Adjust types and formats as needed:
   - **Text**: No transformation
   - **Number**: Specify decimal places (0.00, 0, 0.000)
   - **Date**: Choose output format (YYYY-MM-DD, DD/MM/YYYY, etc.)
   - **Boolean**: Converts Yes/No, Y/N, 1/0, True/False
4. Uncheck columns you want to exclude
5. Click **Preview Cleaned** then **Export to CSV**

#### Supported Transformations

| Input | Output |
|-------|--------|
| `$1,234.56` | `1234.56` |
| `(100.00)` | `-100.00` |
| `12/25/2024` | `2024-12-25` |
| `Yes`, `Y`, `1` | `True` |

---

### 3. Aggregate Data

**Purpose**: Combine multiple CSV files and group data by categories.

#### How to Use

1. Click **Add File** to load multiple CSV files
2. The tool validates that all files share the same schema
3. Preview the combined data
4. Select:
   - **Primary Group By** column
   - **Sum Column** for totals
   - Additional grouping columns (checkboxes)
   - Sort order (by total, count, or name)
5. Click **Aggregate Data**
6. Export results when ready

#### Example Use Cases

- Combine monthly sales reports and group by region
- Aggregate transaction logs by category
- Sum expenses across multiple cost centers

---

### 4. Analyze Data

**Purpose**: Filter data by ranges and calculate statistics.

#### How to Use

1. Select an input CSV file
2. Add filter conditions:
   - **Amount**: Range (e.g., 1000 to 5000)
   - **Date**: Range (e.g., 2024-01-01 to 2024-12-31)
   - **Text**: Contains search (e.g., "invoice")
3. Choose combine mode:
   - **OR**: Match any filter
   - **AND**: Match all filters
4. Click **Apply Filters**
5. Review statistics and export filtered data

#### Statistics Provided

- Record Count
- Sum Total
- Average
- Minimum
- Maximum

---

## Project Structure

```
DataToolKit/
├── src/                    # Source code
│   ├── main.py             # Application entry point
│   ├── home_screen.py      # Tool launcher UI
│   ├── app.py              # Reconciliation tool UI
│   ├── data_cleaner.py     # Data cleaning tool
│   ├── data_aggregator.py  # Data aggregation tool
│   ├── data_analyzer.py    # Data analysis tool
│   ├── base_tool.py        # Shared UI components
│   ├── recon_engine.py     # DuckDB processing engine
│   ├── exporter.py         # CSV export utilities
│   └── models.py           # Data models
├── requirements.txt        # Python dependencies
├── .gitignore              # Git exclusions
└── README.md               # This file
```

---

## Technical Details

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| DuckDB | ≥0.9.0 | SQL-based data processing engine |
| Tkinter | (built-in) | GUI framework |

### Architecture

- **ReconEngine**: Central processing class using DuckDB for SQL operations
- **BaseTool**: Abstract base class providing shared UI patterns
- **Controller Pattern**: Main app manages tool navigation and shared resources

### Performance Notes

- DuckDB enables processing of files with 100k+ rows efficiently
- Data is processed in-memory (no disk I/O during operations)
- Lazy loading of tool modules reduces startup time

---

## Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'X'"**
- Ensure you're running from the project root: `python src/main.py`
- Verify your virtual environment is activated

**Application doesn't start**
- Check Python version: `python --version` (requires 3.10+)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

**Date formats not detected correctly**
- The tool defaults to DD/MM/YYYY (European format) for ambiguous dates
- For US dates, ensure the month is > 12 or use YYYY-MM-DD format

**Large file processing is slow**
- DuckDB handles most files efficiently, but very large files (1M+ rows) may take longer
- Consider filtering or splitting files before processing

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## License

This project is licensed under the MIT License.
