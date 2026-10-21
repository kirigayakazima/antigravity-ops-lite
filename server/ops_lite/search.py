"""Fast, bounded text and symbol search engine with context, globs, and pagination."""

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ops_lite.policy import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_SEARCH_MAX_CHARS,
    DEFAULT_SEARCH_MAX_RESULTS,
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)
from ops_lite.reader import is_binary_file
from ops_lite.results import default_store

HARD_MAX_SEARCH_RESULTS = 50
HARD_MAX_SEARCH_CHARS = 20000


def match_glob_patterns(rel_str: str, patterns: Optional[List[str]]) -> bool:
    """Check if relative path matches any glob pattern."""
    if not patterns:
        return True
    
    # Normalize slashes for glob matching
    normalized = rel_str.replace("\\", "/")
    for pattern in patterns:
        norm_pat = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, norm_pat) or fnmatch.fnmatch(f"/{normalized}", norm_pat):
            return True
        # Match basename
        if fnmatch.fnmatch(Path(normalized).name, norm_pat):
            return True
    return False


def is_path_excluded(
    path: Path,
    root: Path,
    custom_excludes: Optional[List[str]] = None,
) -> bool:
    """Check if path or any of its parents should be ignored."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True

    # Check ignored directories in path components
    for part in rel.parts[:-1]:
        if part in DEFAULT_IGNORED_DIRS:
            return True

    # If it is a directory itself
    if path.is_dir() and path.name in DEFAULT_IGNORED_DIRS:
        return True

    # Check custom excludes
    if custom_excludes:
        rel_str = str(rel).replace("\\", "/")
        for pattern in custom_excludes:
            norm_pat = pattern.replace("\\", "/")
            if fnmatch.fnmatch(rel_str, norm_pat) or fnmatch.fnmatch(path.name, norm_pat):
                return True

    return False


def search_workspace(
    query: str,
    path: str = ".",
    base_root: Optional[str] = None,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    max_results: int = DEFAULT_SEARCH_MAX_RESULTS,
    context_lines: int = 2,
    case_sensitive: bool = False,
) -> Dict[str, Any]:
    """
    Search for query string across text files within path.
    """
    if not query or len(query.strip()) == 0:
        return {
            "query": query,
            "status": "empty_query",
            "matches_returned": 0,
            "total_matches": 0,
            "results": [],
        }

    search_root = validate_and_resolve_path(path, base_root)
    base = search_root if search_root.is_dir() else search_root.parent

    target_query = query if case_sensitive else query.lower()
    effective_max_results = min(max_results, HARD_MAX_SEARCH_RESULTS)
    effective_context = max(0, min(context_lines, 5))

    matched_entries: List[Dict[str, Any]] = []
    formatted_output_lines: List[str] = []
    total_matches_count = 0

    files_to_scan: List[Path] = []
    if search_root.is_file():
        files_to_scan.append(search_root)
    else:
        for p in search_root.rglob("*"):
            if p.is_file():
                if is_path_excluded(p, base, exclude):
                    continue
                rel_str = str(p.relative_to(base)).replace("\\", "/")
                if include and not match_glob_patterns(rel_str, include):
                    continue
                files_to_scan.append(p)

    for file_path in files_to_scan:
        if is_binary_file(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue

        rel_path_str = str(file_path.relative_to(base)).replace("\\", "/")

        for line_idx, line in enumerate(lines):
            line_to_check = line if case_sensitive else line.lower()
            if target_query in line_to_check:
                total_matches_count += 1
                
                # Capture context
                start_c = max(0, line_idx - effective_context)
                end_c = min(len(lines), line_idx + effective_context + 1)
                context_block = []
                for c_idx in range(start_c, end_c):
                    marker = ">" if c_idx == line_idx else " "
                    c_line = lines[c_idx].rstrip("\r\n")
                    context_block.append(f"{marker} {c_idx + 1:4d} | {c_line}")

                entry = {
                    "file": rel_path_str,
                    "line": line_idx + 1,
                    "context": context_block,
                }
                matched_entries.append(entry)

                formatted_output_lines.append(f"--- {rel_path_str}:{line_idx + 1} ---")
                formatted_output_lines.extend(context_block)

    # Check if there are results exceeding the limit
    returned_matches = matched_entries[:effective_max_results]
    returned_output_lines = []
    for m in returned_matches:
        returned_output_lines.append(f"--- {m['file']}:{m['line']} ---")
        returned_output_lines.extend(m["context"])

    joined_text = "\n".join(returned_output_lines)
    truncated_text, is_truncated = truncate_output(joined_text, HARD_MAX_SEARCH_CHARS)
    sanitized_text = redact_sensitive_text(truncated_text)

    result_id: Optional[str] = None
    if total_matches_count > effective_max_results:
        # Store full results for pagination
        result_id = default_store.store(
            result_type="search",
            summary=f"Search '{query}' in '{path}': {total_matches_count} matches found.",
            items=formatted_output_lines,
        )

    return {
        "query": query,
        "search_path": str(search_root),
        "total_matches": total_matches_count,
        "matches_returned": len(returned_matches),
        "has_more": total_matches_count > len(returned_matches),
        "result_id": result_id,
        "is_truncated": is_truncated,
        "output": sanitized_text,
    }
