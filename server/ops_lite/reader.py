"""Bounded and secure file reading with line-numbering, hashing, and truncation controls."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from ops_lite.policy import (
    DEFAULT_READ_MAX_CHARS,
    DEFAULT_READ_MAX_LINES,
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)

HARD_MAX_READ_CHARS = 25000
HARD_MAX_READ_LINES = 500


def is_binary_file(file_path: Path) -> bool:
    """Check if file appears to be binary by inspecting first 4096 bytes for null bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(4096)
            return b"\x00" in chunk
    except OSError:
        return True


def compute_file_hash(file_path: Path) -> str:
    """Compute sha256 hash of file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def read_file_bounded(
    path: str,
    base_root: Optional[str] = None,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_chars: int = DEFAULT_READ_MAX_CHARS,
) -> Dict[str, Any]:
    """
    Read a specific range of lines from a file securely.
    """
    resolved = validate_and_resolve_path(path, base_root)
    
    if not resolved.is_file():
        raise PolicyViolation(f"Target path is not a regular file: '{path}'")

    if is_binary_file(resolved):
        raise PolicyViolation(f"Cannot read binary file: '{path}'")

    file_hash = compute_file_hash(resolved)
    
    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return {
            "error": f"Failed to read file '{path}': {e}",
            "path": path,
            "status": "error",
        }

    total_lines = len(lines)
    start_idx = max(0, start_line - 1)
    
    if end_line is None:
        end_idx = min(total_lines, start_idx + DEFAULT_READ_MAX_LINES)
    else:
        end_idx = min(total_lines, max(start_idx, end_line))
        # Enforce hard line limit
        if (end_idx - start_idx) > HARD_MAX_READ_LINES:
            end_idx = start_idx + HARD_MAX_READ_LINES

    slice_lines = lines[start_idx:end_idx]
    
    # Format with line numbers: " 12 | code line"
    numbered_lines = []
    for offset, line_content in enumerate(slice_lines):
        curr_line_num = start_idx + offset + 1
        # Strip trailing newline for clean display
        clean_line = line_content.rstrip("\r\n")
        numbered_lines.append(f"{curr_line_num:5d} | {clean_line}")

    joined_content = "\n".join(numbered_lines)
    
    # Cap character budget
    effective_max_chars = min(max_chars, HARD_MAX_READ_CHARS)
    truncated_content, is_truncated = truncate_output(
        joined_content,
        effective_max_chars,
        truncation_message="\n... [Content truncated by max_chars limit]",
    )

    sanitized_content = redact_sensitive_text(truncated_content)
    actual_end_line = start_idx + len(slice_lines)
    has_more_lines = actual_end_line < total_lines

    rel_path = str(resolved.relative_to(resolved.anchor if not base_root else Path(base_root).resolve()))

    return {
        "path": rel_path,
        "file_hash": file_hash,
        "total_lines": total_lines,
        "start_line": start_idx + 1,
        "end_line": actual_end_line,
        "has_more_lines": has_more_lines,
        "is_truncated": is_truncated,
        "next_start_line": (actual_end_line + 1) if has_more_lines else None,
        "content": sanitized_content,
    }
