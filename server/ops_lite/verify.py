"""Verification pipeline: runs format, test, and build checks with bounded logs and error extraction."""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ops_lite.policy import (
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)
from ops_lite.results import default_store

MAX_LOG_TAIL_LINES = 25
MAX_LOG_CHARS = 4000


def detect_check_command(root: Path, check_type: str) -> Optional[List[str]]:
    """
    Detect configured test, format, or build commands without guessing arbitrary scripts.
    """
    # 1. Check Node.js package.json scripts
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                scripts = data.get("scripts", {})
                if check_type == "test" and "test" in scripts:
                    return ["npm", "test"]
                elif check_type == "build" and "build" in scripts:
                    return ["npm", "run", "build"]
                elif check_type == "format":
                    if "lint" in scripts:
                        return ["npm", "run", "lint"]
                    elif "format:check" in scripts:
                        return ["npm", "run", "format:check"]
        except Exception:
            pass

    # 2. Check Python
    pyproject = root / "pyproject.toml"
    has_tests_dir = (root / "tests").exists() or (root / "test").exists()
    
    if check_type == "test":
        if has_tests_dir or (root / "pytest.ini").exists() or (root / "tox.ini").exists():
            return ["python", "-m", "pytest"]
        elif (root / "setup.cfg").exists():
            return ["python", "-m", "unittest"]
    elif check_type == "format":
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="ignore")
                if "[tool.ruff]" in content:
                    return ["python", "-m", "ruff", "check", "."]
                elif "[tool.black]" in content:
                    return ["python", "-m", "black", "--check", "."]
                elif "[tool.flake8]" in content:
                    return ["python", "-m", "flake8"]
            except Exception:
                pass
    elif check_type == "build":
        if (root / "setup.py").exists() or pyproject.exists():
            return ["python", "-m", "build"]

    # 3. Check Rust Cargo
    if (root / "Cargo.toml").exists():
        if check_type == "test":
            return ["cargo", "test"]
        elif check_type == "build":
            return ["cargo", "build"]
        elif check_type == "format":
            return ["cargo", "check"]

    # 4. Check Go
    if (root / "go.mod").exists():
        if check_type == "test":
            return ["go", "test", "./..."]
        elif check_type == "build":
            return ["go", "build", "./..."]

    return None


def run_single_check(
    root: Path,
    check_name: str,
    command: List[str],
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Execute a single check command with timeout, exit code capture, and log truncation."""
    start_time = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        elapsed = time.time() - start_time
        exit_code = proc.returncode
        status = "passed" if exit_code == 0 else "failed"
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start_time
        status = "timed_out"
        exit_code = -1
        stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
        stderr = (e.stderr or "") if isinstance(e.stderr, str) else ""
    except Exception as e:
        elapsed = time.time() - start_time
        status = "failed"
        exit_code = -1
        stdout = ""
        stderr = f"Execution failed: {e}"

    full_log_lines = []
    if stdout:
        full_log_lines.extend(stdout.splitlines())
    if stderr:
        full_log_lines.extend(stderr.splitlines())

    result_id = None
    if len(full_log_lines) > MAX_LOG_TAIL_LINES:
        # Store full log for pager
        result_id = default_store.store(
            result_type=f"verify_{check_name}",
            summary=f"Verify check '{check_name}' ({status}, exit {exit_code})",
            items=full_log_lines,
        )
        tail_lines = full_log_lines[-MAX_LOG_TAIL_LINES:]
        log_preview = "\n".join(tail_lines)
    else:
        log_preview = "\n".join(full_log_lines)

    truncated_log, is_truncated = truncate_output(log_preview, MAX_LOG_CHARS)
    sanitized_log = redact_sensitive_text(truncated_log)

    return {
        "check": check_name,
        "status": status,
        "command": " ".join(command),
        "exit_code": exit_code,
        "duration_seconds": round(elapsed, 2),
        "log_preview": sanitized_log,
        "result_id": result_id,
        "is_truncated": is_truncated,
    }


def run_verification_suite(
    path: str = ".",
    base_root: Optional[str] = None,
    checks: Optional[List[str]] = None,
    timeout_seconds: int = 180,
) -> Dict[str, Any]:
    """
    Run requested checks (format, test, build) batch.
    """
    repo_root = validate_and_resolve_path(path, base_root)
    requested_checks = checks or ["test"]
    
    check_results = []
    summary_counts = {
        "passed": 0,
        "failed": 0,
        "timed_out": 0,
        "not_configured": 0,
        "skipped": 0,
    }

    per_check_timeout = max(10, timeout_seconds // max(1, len(requested_checks)))

    for check in requested_checks:
        cmd = detect_check_command(repo_root, check)
        if not cmd:
            summary_counts["not_configured"] += 1
            check_results.append({
                "check": check,
                "status": "not_configured",
                "message": f"No configuration detected for '{check}' in project.",
            })
            continue

        res = run_single_check(
            root=repo_root,
            check_name=check,
            command=cmd,
            timeout_seconds=per_check_timeout,
        )
        summary_counts[res["status"]] = summary_counts.get(res["status"], 0) + 1
        check_results.append(res)

    overall_status = "passed"
    if summary_counts["failed"] > 0:
        overall_status = "failed"
    elif summary_counts["timed_out"] > 0:
        overall_status = "timed_out"
    elif summary_counts["passed"] == 0 and summary_counts["not_configured"] > 0:
        overall_status = "not_configured"

    # Format human-readable summary
    lines = [f"# Verification Suite Result: {overall_status.upper()}"]
    for cr in check_results:
        c_status = cr["status"].upper()
        if c_status == "NOT_CONFIGURED":
            lines.append(f"- **{cr['check']}**: `NOT_CONFIGURED`")
        else:
            lines.append(f"- **{cr['check']}**: `{c_status}` (exit {cr['exit_code']}, took {cr['duration_seconds']}s)")
            if cr.get("log_preview") and cr["status"] != "passed":
                lines.append("  ```text")
                for log_line in cr["log_preview"].splitlines()[-10:]:
                    lines.append(f"  {log_line}")
                lines.append("  ```")
            if cr.get("result_id"):
                lines.append(f"  [Full log stored. Use ops_result id '{cr['result_id']}']")

    return {
        "status": overall_status,
        "counts": summary_counts,
        "results": check_results,
        "summary": "\n".join(lines),
    }
