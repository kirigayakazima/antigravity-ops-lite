"""Bounded and secure file reading with line-numbering, hashing, truncation, deduplication, and multi-file batching."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
HARD_MAX_BATCH_FILES = 32

# In-memory session read deduplication cache: (rel_path, start_line, end_line) -> file_hash
_SESSION_READ_CACHE: Dict[Tuple[str, int, int], str] = {}


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


def clear_read_cache() -> None:
    """Clear session read cache."""
    _SESSION_READ_CACHE.clear()


def read_file_bounded(
    path: str,
    base_root: Optional[str] = None,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_chars: int = DEFAULT_READ_MAX_CHARS,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Read a specific range of lines from a file securely.
    Supports in-session read deduplication if file hash has not changed.
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

    actual_start_line = start_idx + 1
    actual_end_line = end_idx
    rel_root = Path(base_root).resolve() if base_root else resolved.anchor
    try:
        rel_path = str(resolved.relative_to(rel_root)).replace("\\", "/")
    except ValueError:
        rel_path = resolved.name

    cache_key = (rel_path, actual_start_line, actual_end_line)

    # Check read deduplication
    if not force and cache_key in _SESSION_READ_CACHE and _SESSION_READ_CACHE[cache_key] == file_hash:
        return {
            "path": rel_path,
            "file_hash": file_hash,
            "total_lines": total_lines,
            "start_line": actual_start_line,
            "end_line": actual_end_line,
            "has_more_lines": actual_end_line < total_lines,
            "is_truncated": False,
            "is_deduplicated": True,
            "next_start_line": (actual_end_line + 1) if (actual_end_line < total_lines) else None,
            "content": f"[Deduplicated: '{rel_path}' lines {actual_start_line}-{actual_end_line} (SHA-256: {file_hash}) previously read in this session. Pass force=True to re-display]",
        }

    slice_lines = lines[start_idx:end_idx]
    
    # Format with line numbers: " 12 | code line"
    numbered_lines = []
    for offset, line_content in enumerate(slice_lines):
        curr_line_num = start_idx + offset + 1
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
    has_more_lines = actual_end_line < total_lines

    # Update cache
    _SESSION_READ_CACHE[cache_key] = file_hash

    return {
        "path": rel_path,
        "file_hash": file_hash,
        "total_lines": total_lines,
        "start_line": actual_start_line,
        "end_line": actual_end_line,
        "has_more_lines": has_more_lines,
        "is_truncated": is_truncated,
        "is_deduplicated": False,
        "next_start_line": (actual_end_line + 1) if has_more_lines else None,
        "content": sanitized_content,
    }


def read_files_batch(
    files: List[Dict[str, Any]],
    base_root: Optional[str] = None,
    max_chars: int = 15000,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Read bounded ranges across 1-32 files in a single tool call with per-file error isolation.
    """
    if not files or len(files) == 0:
        return {"error": "Files list cannot be empty.", "formatted": "Error: Files list cannot be empty."}

    if len(files) > HARD_MAX_BATCH_FILES:
        return {
            "error": f"Batch exceeds maximum of {HARD_MAX_BATCH_FILES} files.",
            "formatted": f"Error: Batch exceeds maximum of {HARD_MAX_BATCH_FILES} files.",
        }

    file_results = []
    blocks = []
    total_files = len(files)
    successful_count = 0

    per_file_chars = max(1500, max_chars // max(1, total_files))

    for item in files:
        fpath = item.get("path")
        s_line = item.get("start_line", 1)
        e_line = item.get("end_line")

        if not fpath:
            blocks.append("### File: [Unknown] (Error: Missing 'path')\n")
            continue

        try:
            res = read_file_bounded(
                path=fpath,
                base_root=base_root,
                start_line=s_line,
                end_line=e_line,
                max_chars=per_file_chars,
                force=force,
            )
            file_results.append(res)
            if "error" in res:
                blocks.append(f"### File: {fpath} (Error: {res['error']})\n")
            else:
                successful_count += 1
                dedup_note = " [DEDUPLICATED]" if res.get("is_deduplicated") else ""
                header = f"### File: `{res['path']}` (lines {res['start_line']}-{res['end_line']} of {res['total_lines']}) [SHA-256: {res['file_hash']}]{dedup_note}"
                content = res["content"]
                block = f"{header}\n```\n{content}\n```"
                if res.get("has_more_lines"):
                    block += f"\n> More lines in `{res['path']}`. Next start: {res['next_start_line']}"
                blocks.append(block)
        except Exception as e:
            blocks.append(f"### File: `{fpath}` (Policy / Error: {e})\n")

    summary_header = f"# Multi-File Read: {successful_count}/{total_files} files retrieved successfully"
    full_text = summary_header + "\n\n" + "\n\n".join(blocks)
    truncated, is_trunc = truncate_output(full_text, max_chars)

    return {
        "total_files": total_files,
        "successful_count": successful_count,
        "is_truncated": is_trunc,
        "results": file_results,
        "formatted": truncated,
    }
