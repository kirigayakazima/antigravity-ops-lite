---
name: data-inspection
description: >-
  Inspect CSV, TSV, and tabular dataset files safely using ops_read_table with automatic delimiter
  detection, aligned markdown preview, and row-level pagination.
---

# Data & Tabular Inspection Runbook

Use this skill when inspecting tabular datasets, benchmark exports, logs, or metrics stored in CSV or TSV format.

## Step-by-Step Workflow

1. **Locate Data Files**:
   - Use `ops_glob(patterns=["**/*.csv", "**/*.tsv"])` to discover available dataset files.

2. **Bounded Table Reading**:
   - Call `ops_read_table(path="data.csv", offset=1, limit=20)` to preview the first 20 rows.
   - The tool automatically detects delimiters (comma, tab, semicolon, pipe) and formats the output into a clean, aligned Markdown table.

3. **Paginate Records**:
   - If further rows need analysis, advance `offset` (e.g. `offset=21, limit=20`).
   - Do NOT attempt to read entire megabyte-sized CSV files into context with raw file read tools.
