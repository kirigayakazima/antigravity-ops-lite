"""Antigravity 2.0 ops-lite MCP Server: Script-First and Token-Optimized Operations."""

import json
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from ops_lite.git_ops import get_git_summary
from ops_lite.policy import (
    DEFAULT_READ_MAX_CHARS,
    DEFAULT_SEARCH_MAX_RESULTS,
    DEFAULT_SUMMARY_MAX_ITEMS,
    PolicyViolation,
    redact_sensitive_text,
)
from ops_lite.project import summarize_project
from ops_lite.reader import read_file_bounded
from ops_lite.results import default_store
from ops_lite.search import search_workspace
from ops_lite.verify import run_verification_suite

app = MCPServer(
    name="ops-lite",
    instructions="High-efficiency, token-budgeted repository inspection, search, reading, and verification.",
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
    description="Bounded file reader returning 1-indexed line numbers, file hash, and truncation status. Rejects binary and secret files.",
)
def ops_read(
    path: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_chars: int = DEFAULT_READ_MAX_CHARS,
) -> str:
    """Read a specific range of lines from a source file securely."""
    try:
        res = read_file_bounded(
            path=path,
            start_line=start_line,
            end_line=end_line,
            max_chars=max_chars,
        )
        if "error" in res:
            return f"Error reading file '{path}': {res['error']}"

        lines = [
            f"# File: {res['path']} (lines {res['start_line']}-{res['end_line']} of {res['total_lines']}) [SHA-256: {res['file_hash']}]",
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
    # Ensure stdout is unbuffered and clean for JSON-RPC messages
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
