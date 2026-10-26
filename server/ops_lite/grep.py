"""Advanced file discovery (ops_glob) and regular expression search (ops_grep)."""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ops_lite.policy import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_SEARCH_MAX_CHARS,
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)
from ops_lite.reader import is_binary_file
from ops_lite.results import default_store

HARD_MAX_GLOB_ENTRIES = 500
HARD_MAX_GREP_RESULTS = 100
HARD_MAX_GREP_CHARS = 25000


def glob_files(
    path: str = ".",
    patterns: Optional[List[str]] = None,
    output_mode: str = "paths",  # "paths" | "details"
    sort: str = "path",          # "path" | "modified"
    limit: int = 100,
    base_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find regular files matching patterns below path.
    Supports negative glob patterns with '!' prefix (e.g. '!vendor/**').
    """
    root = validate_and_resolve_path(path, base_root)
    if not root.is_dir():
        raise PolicyViolation(f"Path is not a directory: '{path}'")

    pat_list = patterns or ["*"]
    positive_pats = [p for p in pat_list if not p.startswith("!")]
    negative_pats = [p[1:] for p in pat_list if p.startswith("!")]

    if not positive_pats:
        positive_pats = ["*"]

    matched_entries: List[Dict[str, Any]] = []

    for entry in root.rglob("*"):
        if not entry.is_file():
            continue

        try:
            rel = entry.relative_to(root)
        except ValueError:
            continue

        # Skip ignored directories
        parts = rel.parts[:-1]
        if any(p in DEFAULT_IGNORED_DIRS for p in parts):
            continue

        rel_str = str(rel).replace("\\", "/")
        file_name = entry.name

        # Match positive patterns
        matched = False
        for pat in positive_pats:
            norm_pat = pat.replace("\\", "/")
            if (
                fnmatch.fnmatch(rel_str, norm_pat)
                or fnmatch.fnmatch(file_name, norm_pat)
                or fnmatch.fnmatch(f"/{rel_str}", norm_pat)
            ):
                matched = True
                break

        if not matched:
            continue

        # Check negative patterns
        excluded = False
        for npat in negative_pats:
            norm_npat = npat.replace("\\", "/")
            if (
                fnmatch.fnmatch(rel_str, norm_npat)
                or fnmatch.fnmatch(file_name, norm_npat)
                or fnmatch.fnmatch(f"/{rel_str}", norm_npat)
            ):
                excluded = True
                break

        if excluded:
            continue

        try:
            st = entry.stat()
            matched_entries.append({
                "path": rel_str,
                "bytes": st.st_size,
                "modified": int(st.st_mtime * 1000),
            })
        except OSError:
            matched_entries.append({
                "path": rel_str,
                "bytes": 0,
                "modified": 0,
            })

    # Sort
    if sort == "modified":
        matched_entries.sort(key=lambda x: x["modified"], reverse=True)
    else:
        matched_entries.sort(key=lambda x: x["path"].lower())

    total = len(matched_entries)
    effective_limit = min(limit, HARD_MAX_GLOB_ENTRIES)
    slice_entries = matched_entries[:effective_limit]

    # Format output
    lines = [f"# Glob: {len(slice_entries)} files (Total matched: {total})"]
    if output_mode == "details":
        lines.append("| Path | Size | Last Modified |")
        lines.append("| :--- | :--- | :--- |")
        for it in slice_entries:
            import datetime
            dt = datetime.datetime.fromtimestamp(it["modified"] / 1000).strftime("%Y-%m-%d %H:%M")
            lines.append(f"| `{it['path']}` | {it['bytes']} B | {dt} |")
    else:
        for it in slice_entries:
            lines.append(f"- {it['path']}")

    if total > effective_limit:
        lines.append(f"\n> Note: {total - effective_limit} more files omitted. Narrow patterns or increase limit.")

    return {
        "total": total,
        "returned": len(slice_entries),
        "items": slice_entries,
        "formatted": "\n".join(lines),
    }


def grep_workspace(
    pattern: str,
    path: str = ".",
    glob: Optional[List[str]] = None,
    output_mode: str = "content",  # "content" | "files_with_matches" | "count" | "summary"
    case_insensitive: bool = False,
    before_context: int = 0,
    after_context: int = 0,
    max_results: int = 50,
    base_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search UTF-8 files with regular expression, bounded output, and multiple output modes.
    """
    if not pattern:
        return {"error": "Pattern cannot be empty", "formatted": "Error: Pattern cannot be empty"}

    root = validate_and_resolve_path(path, base_root)
    base = root if root.is_dir() else root.parent

    # Compile regex
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid regular expression: {e}", "formatted": f"Error: Invalid regular expression '{pattern}': {e}"}

    effective_before = max(0, min(before_context, 10))
    effective_after = max(0, min(after_context, 10))
    effective_max = min(max_results, HARD_MAX_GREP_RESULTS)

    # Gather files
    files_to_scan: List[Path] = []
    if root.is_file():
        files_to_scan.append(root)
    else:
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            try:
                rel = entry.relative_to(base)
            except ValueError:
                continue

            # Default ignored directories
            if any(p in DEFAULT_IGNORED_DIRS for p in rel.parts[:-1]):
                continue

            rel_str = str(rel).replace("\\", "/")
            if glob:
                # Filter by glob
                matched = False
                for g in glob:
                    norm_g = g.replace("\\", "/")
                    if fnmatch.fnmatch(rel_str, norm_g) or fnmatch.fnmatch(entry.name, norm_g):
                        matched = True
                        break
                if not matched:
                    continue

            files_to_scan.append(entry)

    matches_by_file: Dict[str, List[Dict[str, Any]]] = {}
    file_match_counts: Dict[str, int] = {}
    total_matches = 0
    skipped_binary = 0

    for fpath in files_to_scan:
        if is_binary_file(fpath):
            skipped_binary += 1
            continue

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue

        rel_path_str = str(fpath.relative_to(base)).replace("\\", "/")
        file_matches = []

        for idx, line in enumerate(lines):
            if regex.search(line):
                total_matches += 1
                file_match_counts[rel_path_str] = file_match_counts.get(rel_path_str, 0) + 1

                if output_mode == "content" and len(file_matches) < effective_max:
                    start_c = max(0, idx - effective_before)
                    end_c = min(len(lines), idx + effective_after + 1)
                    ctx = []
                    for c_idx in range(start_c, end_c):
                        marker = ">" if c_idx == idx else " "
                        ctx.append(f"{marker} {c_idx + 1:4d} | {lines[c_idx].rstrip(chr(10)).rstrip(chr(13))}")
                    file_matches.append({
                        "line": idx + 1,
                        "context": ctx,
                    })

        if file_matches:
            matches_by_file[rel_path_str] = file_matches

    # Render according to output_mode
    lines = []
    result_id = None

    if output_mode == "summary":
        lines.append(f"# Grep Summary: /{pattern}/")
        lines.append(f"- **Total Matches**: {total_matches}")
        lines.append(f"- **Matching Files**: {len(file_match_counts)}")
        lines.append(f"- **Scanned Files**: {len(files_to_scan)}")
        if skipped_binary:
            lines.append(f"- **Skipped Binary Files**: {skipped_binary}")

    elif output_mode == "files_with_matches":
        lines.append(f"# Grep Files with Matches: /{pattern}/ ({len(file_match_counts)} files)")
        for f in sorted(file_match_counts.keys()):
            lines.append(f"- `{f}` ({file_match_counts[f]} matches)")

    elif output_mode == "count":
        lines.append(f"# Grep Match Counts: /{pattern}/ ({total_matches} total matches in {len(file_match_counts)} files)")
        for f in sorted(file_match_counts.keys(), key=lambda k: file_match_counts[k], reverse=True):
            lines.append(f"- `{f}`: {file_match_counts[f]}")

    else:  # "content"
        lines.append(f"# Grep Results: /{pattern}/ ({total_matches} matches)")
        match_count = 0
        all_formatted_items = []
        for fpath_str, fmatches in matches_by_file.items():
            for m in fmatches:
                match_count += 1
                if match_count <= effective_max:
                    lines.append(f"\n--- {fpath_str}:{m['line']} ---")
                    lines.extend(m["context"])
                
                # Collect for pagination
                all_formatted_items.append(f"--- {fpath_str}:{m['line']} ---")
                all_formatted_items.extend(m["context"])

        if total_matches > effective_max:
            result_id = default_store.store(
                result_type="grep",
                summary=f"Grep /{pattern}/: {total_matches} matches across {len(file_match_counts)} files",
                items=all_formatted_items,
            )
            lines.append(f"\n> Note: {total_matches - effective_max} matches omitted. Use ops_result(result_id='{result_id}', offset={effective_max}) to page.")

    joined = "\n".join(lines)
    truncated, is_trunc = truncate_output(joined, HARD_MAX_GREP_CHARS)
    sanitized = redact_sensitive_text(truncated)

    return {
        "pattern": pattern,
        "total_matches": total_matches,
        "files_matched": len(file_match_counts),
        "result_id": result_id,
        "is_truncated": is_trunc,
        "formatted": sanitized,
    }
