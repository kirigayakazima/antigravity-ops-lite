"""Antigravity 2.0 ops-lite MCP Server: Script-First and Token-Optimized Operations."""

import json
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from ops_lite.batch import execute_batch_operations, replace_literal_in_files
from ops_lite.git_ops import get_git_summary
from ops_lite.grep import glob_files, grep_workspace
from ops_lite.policy import (
    DEFAULT_READ_MAX_CHARS,
    DEFAULT_SEARCH_MAX_RESULTS,
    DEFAULT_SUMMARY_MAX_ITEMS,
    PolicyViolation,
    redact_sensitive_text,
)
from ops_lite.project import summarize_project
from ops_lite.reader import read_file_bounded, read_files_batch
from ops_lite.results import default_store
from ops_lite.search import search_workspace
from ops_lite.table import read_table_bounded
from ops_lite.verify import run_verification_suite

app = MCPServer(
    name="ops-lite",
    instructions="High-efficiency, token-budgeted repository operations: multi-file inspection, bounded reading, glob, grep, safe batching, and verification.",
)


@app.tool(
    name="ops_summary",
    description="Inspect project metadata, entrypoints, configured scripts, git branch, and directory tree without flooding context. Ideal first step.",
)
def ops_summary(
    path: str = ".",
    sections: Optional[List[str]] = None,
    max_items: int = DEFAULT_SUMMARY_MAX_ITEMS,
) -> str:
    """Inspect project metadata, entrypoints, and directory tree structure."""
    try:
        res = summarize_project(path=path, sections=sections, max_items=max_items)
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_summary: {e}"


@app.tool(
    name="ops_search",
    description="Bounded code and symbol search with context lines, globs, and auto-pagination. Excludes build artifacts and dependencies.",
)
def ops_search(
    query: str,
    path: str = ".",
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    max_results: int = DEFAULT_SEARCH_MAX_RESULTS,
    context_lines: int = 2,
    case_sensitive: bool = False,
) -> str:
    """Search for symbol, function, or text pattern within workspace."""
    try:
        res = search_workspace(
            query=query,
            path=path,
            include=include,
            exclude=exclude,
            max_results=max_results,
            context_lines=context_lines,
            case_sensitive=case_sensitive,
        )
        lines = [
            f"# Search Results: '{query}' (Found {res['total_matches']} matches, showing {res['matches_returned']})",
        ]
        if res.get("result_id"):
            lines.append(f"> Note: More matches exist. Use ops_result(result_id='{res['result_id']}', offset={res['matches_returned']}) to retrieve more.")
        lines.append("")
        lines.append(res.get("output", ""))
        return "\n".join(lines)
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_search: {e}"


@app.tool(
    name="ops_read",
    description="Bounded single-file reader returning 1-indexed line numbers, file hash, and deduplication detection. Rejects binary and secret files.",
)
def ops_read(
    path: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_chars: int = DEFAULT_READ_MAX_CHARS,
    force: bool = False,
) -> str:
    """Read a specific range of lines from a source file securely."""
    try:
        res = read_file_bounded(
            path=path,
            start_line=start_line,
            end_line=end_line,
            max_chars=max_chars,
            force=force,
        )
        if "error" in res:
            return f"Error reading file '{path}': {res['error']}"

        dedup_tag = " [DEDUPLICATED]" if res.get("is_deduplicated") else ""
        lines = [
            f"# File: {res['path']} (lines {res['start_line']}-{res['end_line']} of {res['total_lines']}) [SHA-256: {res['file_hash']}]{dedup_tag}",
            "```",
            res["content"],
            "```",
        ]
        if res.get("has_more_lines"):
            lines.append(f"> Note: File has more lines. Use ops_read(path='{path}', start_line={res['next_start_line']}) to continue.")
        return "\n".join(lines)
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_read: {e}"


@app.tool(
    name="ops_read_files",
    description="Batch read bounded ranges across 1-32 files in a single tool call. Each item: {'path': '...', 'start_line': 1, 'end_line': 100}.",
)
def ops_read_files(
    files: List[Dict[str, Any]],
    max_chars: int = 15000,
    force: bool = False,
) -> str:
    """Batch read multiple files with per-file error isolation and line budgets."""
    try:
        res = read_files_batch(files=files, max_chars=max_chars, force=force)
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_read_files: {e}"


@app.tool(
    name="ops_glob",
    description="Locate files by glob patterns (e.g. ['**/*.py', '!tests/**']). Output modes: 'paths' or 'details' (with size & modified time).",
)
def ops_glob(
    path: str = ".",
    patterns: Optional[List[str]] = None,
    output_mode: str = "paths",
    sort: str = "path",
    limit: int = 100,
) -> str:
    """Find files using glob patterns with sorting and size details."""
    try:
        res = glob_files(
            path=path,
            patterns=patterns,
            output_mode=output_mode,
            sort=sort,
            limit=limit,
        )
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_glob: {e}"


@app.tool(
    name="ops_grep",
    description="Regex search with multiple output modes: 'content' (lines + context), 'files_with_matches' (filenames only), 'count', or 'summary'.",
)
def ops_grep(
    pattern: str,
    path: str = ".",
    glob: Optional[List[str]] = None,
    output_mode: str = "content",
    case_insensitive: bool = False,
    before_context: int = 0,
    after_context: int = 0,
    max_results: int = 50,
) -> str:
    """Regular expression search across UTF-8 workspace files."""
    try:
        res = grep_workspace(
            pattern=pattern,
            path=path,
            glob=glob,
            output_mode=output_mode,
            case_insensitive=case_insensitive,
            before_context=before_context,
            after_context=after_context,
            max_results=max_results,
        )
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_grep: {e}"


@app.tool(
    name="ops_replace",
    description="Deterministic literal text replacement across workspace files. Previews with dry_run=True (default), applies with dry_run=False.",
)
def ops_replace(
    pattern: str,
    replacement: str,
    path: str = ".",
    glob: Optional[List[str]] = None,
    max_replacements: int = 50,
    dry_run: bool = True,
) -> str:
    """Mechanical cross-file literal text replacement without manual diff creation."""
    try:
        res = replace_literal_in_files(
            pattern=pattern,
            replacement=replacement,
            path=path,
            glob=glob,
            max_replacements=max_replacements,
            dry_run=dry_run,
        )
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_replace: {e}"


@app.tool(
    name="ops_batch",
    description="Plan and execute safe file operations: copy, move, remove. Action: 'plan' (preview & validate) or 'run' (execute).",
)
def ops_batch(
    action: str,
    operations: List[Dict[str, Any]],
    root: str = ".",
) -> str:
    """Execute preflight-verified batch file operations."""
    try:
        res = execute_batch_operations(action=action, operations=operations, root=root)
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_batch: {e}"


@app.tool(
    name="ops_read_table",
    description="Bounded CSV/TSV reader. Renders clean, aligned markdown tables with column alignment, row pagination, and character caps.",
)
def ops_read_table(
    path: str,
    offset: int = 1,
    limit: int = 50,
    delimiter: Optional[str] = None,
    max_chars: int = 8000,
) -> str:
    """Read structured tabular data (CSV/TSV) safely."""
    try:
        res = read_table_bounded(
            path=path,
            offset=offset,
            limit=limit,
            delimiter=delimiter,
            max_chars=max_chars,
        )
        return res.get("formatted", str(res))
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_read_table: {e}"


@app.tool(
    name="ops_run",
    description="Execute deterministic batch checks: 'verify' (format/test/build), 'git_summary' (diff/status), or 'inspect'. Arbitrary shell commands are denied.",
)
def ops_run(
    task: str,
    checks: Optional[List[str]] = None,
    path: str = ".",
    timeout_seconds: int = 180,
) -> str:
    """Execute pre-configured verification or git summary task batch."""
    try:
        task_clean = task.strip().lower()
        if task_clean == "verify":
            res = run_verification_suite(
                path=path,
                checks=checks or ["test"],
                timeout_seconds=timeout_seconds,
            )
            return res.get("summary", json.dumps(res, indent=2))
        elif task_clean == "git_summary":
            res = get_git_summary(path=path)
            return res.get("formatted", str(res))
        elif task_clean == "inspect":
            res = summarize_project(path=path)
            return res.get("formatted", str(res))
        else:
            return (
                f"Error: Unsupported task '{task}'. Supported tasks are: "
                "'verify' (runs configured checks), 'git_summary' (status & diff), 'inspect' (project overview)."
            )
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_run: {e}"


@app.tool(
    name="ops_result",
    description="Retrieve paginated logs or large outputs produced by previous ops tools using their result_id.",
)
def ops_result(
    result_id: str,
    offset: int = 0,
    limit: int = 20,
) -> str:
    """Retrieve paginated slices of large operation outputs."""
    try:
        res = default_store.retrieve(result_id=result_id, offset=offset, limit=limit)
        if "error" in res:
            return f"Error: {res['error']}"

        lines = [
            f"# Result: {res['result_id']} (Type: {res['result_type']}, Items {res['offset']}-{res['offset'] + len(res['items'])} of {res['total_items']})",
            f"> Summary: {res['summary']}",
            "```text",
            "\n".join(res["items"]),
            "```",
        ]
        if res.get("has_more"):
            lines.append(f"> Note: More items available. Use ops_result(result_id='{result_id}', offset={res['offset'] + res['limit']})")
        return "\n".join(lines)
    except PolicyViolation as pv:
        return f"Error (Policy Violation): {pv}"
    except Exception as e:
        return f"Error executing ops_result: {e}"


def main():
    """Run the MCP server over stdio transport."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
