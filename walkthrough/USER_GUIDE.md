# Data Processing Toolkit - User Guide

Step-by-step instructions for using each tool in the Data Processing Toolkit.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Reconcile Files](#-reconcile-files)
3. [Clean Data](#-clean-data)
4. [Aggregate Data](#-aggregate-data)
5. [Analyze Data](#-analyze-data)

---

## Getting Started

### Launching the Application

```powershell
cd d:\Projects\Recon2
python main.py
```

The home screen displays all available tools. Click any tool button to open it.

### Navigation

- Click **← Back to Home** in any tool to return to the home screen
- Right-click any cell in a table to copy its value
- All tools support large files (500K+ rows)

---

## 🔄 Reconcile Files

**Purpose:** Compare two CSV files and identify matches, differences, and missing records.

### Step 1: Load Files
1. Click **Browse** next to "Source A" and select your first CSV file
2. Click **Browse** next to "Source B" and select your second CSV file
3. The file preview shows the first 3 rows of each file

### Step 2: Configure Column Mapping
The tool auto-detects columns, but you can adjust:
- **Date Column:** The date field in each file
- **Amount Column:** The numeric field to compare
- **Description (optional):** Additional context field
- **Match Key:** The field used to match records (e.g., Invoice Number)

### Step 3: Set Tolerance
- Enter an **Amount Tolerance** (e.g., 0.01 for penny differences)
- Records within tolerance are considered matches

### Step 4: Run Reconciliation
1. Click **▶ Run Reconciliation**
2. View results in tabs:
   - **Exact Matches:** Records that match perfectly
   - **Date Notes:** Amounts match but dates differ
   - **Amount Variances:** Records with amount differences
   - **Missing in B:** Records in A not found in B
   - **Missing in A:** Records in B not found in A

### Step 5: Export Results
- Click **Export All** to save all result tabs
- Click **Export Current Tab** to save just the active tab

---

## 🧹 Clean Data

**Purpose:** Standardize data formats and remove unwanted columns.

### Step 1: Load File
1. Click **Browse** and select your CSV file
2. The preview shows the first 5 rows

### Step 2: Configure Columns
For each column, set:
- **Include:** Check to keep the column in output (uncheck to exclude)
- **Data Type:** Text, Number, Date, or Boolean
- **Format:** Output format (e.g., YYYY-MM-DD for dates)

#### Data Type Options

| Type | What It Does | Format Options |
|------|--------------|----------------|
| Text | No changes | None |
| Number | Removes $, commas, symbols | 0.00, 0, 0.000 |
| Date | Standardizes date formats | YYYY-MM-DD, DD/MM/YYYY, etc. |
| Boolean | Converts Yes/No, 1/0 to True/False | None |

### Step 3: Preview & Export
1. Click **Auto-Detect Types** to automatically set types based on column names
2. Click **Preview Cleaned** to see the transformed data
3. Click **Export to CSV** to save the cleaned file

---

## 📊 Aggregate Data

**Purpose:** Combine multiple CSV files and create grouped summaries.

### Step 1: Add Files
1. Click **Add File** to select CSV files
2. Add multiple files (they must have the same columns)
3. The status shows if files are compatible

> ⚠️ All files must have identical column names to combine

### Step 2: View Combined Data
- The preview shows sample rows from all combined files
- Total row count is displayed

### Step 3: Configure Aggregation
- **Primary Group By:** The main category to group by
- **Sum Column:** The numeric column to total
- **Additional Grouping:** Check boxes for extra grouping levels
- **Sort By:** Order results by Total, Count, or Group Name

### Step 4: Aggregate & Export
1. Click **Aggregate Data** to run the grouping
2. View results showing:
   - Group values
   - Record count per group
   - Total amount per group
   - Grand total at the bottom
3. Click **Export Results** to save

### Example
If you have sales data grouped by Category:
```
Category    | Count | Total Amount
------------|-------|-------------
Electronics |   45  |   12,500.00
Clothing    |   32  |    8,750.50
Food        |   89  |    3,200.00
------------|-------|-------------
Grand Total |  166  |   24,450.50
```

---

## 🔍 Analyze Data

**Purpose:** Filter data by ranges and calculate statistics.

### Step 1: Load File
1. Click **Browse** and select your CSV file
2. The preview shows all data

### Step 2: Add Filters
1. Select **Filter Type:**
   - **Amount:** Filter by numeric range
   - **Date:** Filter by date range
   - **Text:** Search for text containing a value

2. Select the **Column** to filter

3. Enter values:
   - For Amount/Date: Enter **From** and **To** values
   - For Text: Enter the search text in **From**

4. Click **Add Range** to add the filter

### Step 3: Combine Multiple Filters
- Add multiple filters to narrow results
- Choose combine mode:
  - **OR (Any Match):** Records matching ANY filter
  - **AND (All Must Match):** Records matching ALL filters

### Step 4: Apply & View Results
1. Select the **Analyze Column** for statistics
2. Click **Apply Filters**
3. View statistics:
   - Matched Records (count)
   - Total Sum
   - Average
   - Min / Max values
4. Preview shows filtered records

### Step 5: Export
- Click **Export Filtered Data** to save matching records

### Example Filters
| Filter Type | Column | From | To | Result |
|-------------|--------|------|-----|--------|
| Amount | Amount | 100 | 500 | Records between $100-$500 |
| Date | Date | 2024-01-01 | 2024-03-31 | Q1 2024 records |
| Text | Description | refund | - | Records containing "refund" |

---

## Tips & Tricks

### Performance
- Files up to 500MB process quickly
- For very large files, processing happens in the background

### Common Issues

| Issue | Solution |
|-------|----------|
| Columns not detected | Check CSV has headers in first row |
| Date parsing wrong | Select correct date column in mapping |
| Amount has $ symbols | Enable auto-clean or use Clean Data tool first |
| Files won't combine | Ensure all files have identical column names |

### Keyboard Shortcuts
- **Right-click:** Copy cell value
- **Scroll wheel:** Navigate large tables

---

## Support

For issues or feature requests, refer to the `IMPLEMENTATION_PLAN.md` for technical details.
