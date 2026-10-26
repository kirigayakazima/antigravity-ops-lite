"""Bounded CSV/TSV table reader and formatter (ops_read_table)."""

import csv
import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from ops_lite.policy import (
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)
from ops_lite.reader import compute_file_hash, is_binary_file

HARD_MAX_TABLE_ROWS = 200
HARD_MAX_TABLE_CHARS = 15000


def read_table_bounded(
    path: str,
    offset: int = 1,
    limit: int = 50,
    delimiter: Optional[str] = None,
    max_chars: int = 8000,
    base_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read bounded tabular data (CSV/TSV) and format as a compact markdown table.
    offset is 1-based data row index (row 1 is first row after header).
    """
    resolved = validate_and_resolve_path(path, base_root)
    if not resolved.is_file():
        raise PolicyViolation(f"Path is not a regular file: '{path}'")

    if is_binary_file(resolved):
        raise PolicyViolation(f"Cannot read binary file: '{path}'")

    file_hash = compute_file_hash(resolved)

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            
            # Detect delimiter if not specified
            if not delimiter:
                if resolved.suffix.lower() == ".tsv":
                    effective_delim = "\t"
                else:
                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                        effective_delim = dialect.delimiter
                    except Exception:
                        effective_delim = ","
            else:
                effective_delim = delimiter

            reader = csv.reader(f, delimiter=effective_delim)
            all_rows = list(reader)
    except Exception as e:
        return {"error": f"Failed to parse table '{path}': {e}", "formatted": f"Error parsing table: {e}"}

    if not all_rows:
        return {
            "path": path,
            "total_rows": 0,
            "columns": [],
            "formatted": f"# Table: {path} (Empty file)",
        }

    header = all_rows[0]
    data_rows = all_rows[1:]
    total_data_rows = len(data_rows)

    start_idx = max(0, offset - 1)
    effective_limit = min(limit, HARD_MAX_TABLE_ROWS)
    end_idx = min(total_data_rows, start_idx + effective_limit)
    slice_rows = data_rows[start_idx:end_idx]

    # Clean cells
    cleaned_header = [h.strip().replace("\n", " ").replace("|", "\\|") for h in header]
    num_cols = len(cleaned_header)

    lines = [
        f"# Table: {resolved.name} (Rows {start_idx + 1}-{end_idx} of {total_data_rows}) [SHA-256: {file_hash}]",
        "",
        "| # | " + " | ".join(cleaned_header) + " |",
        "| -: | " + " | ".join(["---"] * num_cols) + " |",
    ]

    for r_idx, row in enumerate(slice_rows):
        curr_num = start_idx + r_idx + 1
        cells = [c.strip().replace("\n", " ").replace("|", "\\|") for c in row]
        # Pad or trim to match header column count
        if len(cells) < num_cols:
            cells.extend([""] * (num_cols - len(cells)))
        elif len(cells) > num_cols:
            cells = cells[:num_cols]
        lines.append(f"| {curr_num} | " + " | ".join(cells) + " |")

    has_more = end_idx < total_data_rows
    if has_more:
        lines.append(f"\n> Note: More rows available. Use ops_read_table(path='{path}', offset={end_idx + 1})")

    joined = "\n".join(lines)
    effective_max_chars = min(max_chars, HARD_MAX_TABLE_CHARS)
    truncated, is_trunc = truncate_output(joined, effective_max_chars)
    sanitized = redact_sensitive_text(truncated)

    return {
        "path": str(resolved),
        "file_hash": file_hash,
        "total_rows": total_data_rows,
        "offset": offset,
        "limit": effective_limit,
        "has_more": has_more,
        "is_truncated": is_trunc,
        "formatted": sanitized,
    }
