"""Git status, diff summarization, and safe change inspection."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ops_lite.policy import (
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)
from ops_lite.results import default_store

MAX_GIT_SUMMARY_CHARS = 8000
MAX_DIFF_SNIPPET_LINES = 120


def get_git_summary(
    path: str = ".",
    base_root: Optional[str] = None,
    include_diff: bool = True,
) -> Dict[str, Any]:
    """
    Produce a compact, token-friendly summary of git working tree status and diff.
    """
    repo_root = validate_and_resolve_path(path, base_root)
    if not (repo_root / ".git").exists():
        return {
            "is_git": False,
            "status": "not_a_git_repository",
            "message": f"Directory '{path}' is not inside a Git repository.",
        }

    try:
        # Branch
        res_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = res_branch.stdout.strip() or "HEAD detached"

        # Short status
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        status_lines = [l.rstrip("\r\n") for l in res_status.stdout.splitlines() if l.strip()]

        staged_files = []
        unstaged_files = []
        untracked_files = []

        for line in status_lines:
            if len(line) < 3:
                continue
            idx_char = line[0]
            work_char = line[1]
            fname = line[3:].strip()
            if idx_char == "?" and work_char == "?":
                untracked_files.append(fname)
            else:
                if idx_char not in (" ", "?"):
                    staged_files.append(f"{idx_char} {fname}")
                if work_char not in (" ", "?"):
                    unstaged_files.append(f"{work_char} {fname}")

        # Diff stat
        res_stat = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        diff_stat = res_stat.stdout.strip()

        # Diff snippet
        diff_snippet = ""
        result_id = None
        if include_diff and (staged_files or unstaged_files):
            res_diff = subprocess.run(
                ["git", "diff", "--unified=3"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=15,
            )
            raw_diff_lines = res_diff.stdout.splitlines()
            if len(raw_diff_lines) > MAX_DIFF_SNIPPET_LINES:
                # Store full diff in ResultStore
                result_id = default_store.store(
                    result_type="git_diff",
                    summary=f"Git diff for branch {branch} ({len(raw_diff_lines)} lines)",
                    items=raw_diff_lines,
                )
                preview_lines = raw_diff_lines[:MAX_DIFF_SNIPPET_LINES]
                preview_lines.append(f"\n... [Diff truncated: total {len(raw_diff_lines)} lines, use ops_result with id '{result_id}' to paginate]")
                diff_snippet = "\n".join(preview_lines)
            else:
                diff_snippet = "\n".join(raw_diff_lines)

        summary_lines = [
            f"# Git Summary ({branch})",
            f"- Modified/Unstaged: {len(unstaged_files)}",
            f"- Staged: {len(staged_files)}",
            f"- Untracked: {len(untracked_files)}",
        ]
        if unstaged_files:
            summary_lines.append("## Unstaged Changes:")
            for f in unstaged_files[:10]:
                summary_lines.append(f"  {f}")
            if len(unstaged_files) > 10:
                summary_lines.append(f"  ... and {len(unstaged_files) - 10} more")

        if staged_files:
            summary_lines.append("## Staged Changes:")
            for f in staged_files[:10]:
                summary_lines.append(f"  {f}")

        if diff_stat:
            summary_lines.append("\n## Diff Stat:")
            summary_lines.append(diff_stat)

        if diff_snippet:
            summary_lines.append("\n## Diff Snippet:")
            summary_lines.append("```diff")
            summary_lines.append(diff_snippet)
            summary_lines.append("```")

        formatted = "\n".join(summary_lines)
        truncated, is_truncated = truncate_output(formatted, MAX_GIT_SUMMARY_CHARS)
        sanitized = redact_sensitive_text(truncated)

        return {
            "is_git": True,
            "branch": branch,
            "staged_count": len(staged_files),
            "unstaged_count": len(unstaged_files),
            "untracked_count": len(untracked_files),
            "result_id": result_id,
            "is_truncated": is_truncated,
            "formatted": sanitized,
        }
    except Exception as e:
        return {
            "is_git": True,
            "error": f"Failed to execute git command: {e}",
            "status": "error",
        }
