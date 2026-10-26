"""Safe file batch operations (ops_batch) and deterministic cross-file replacement (ops_replace)."""

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ops_lite.policy import (
    DEFAULT_IGNORED_DIRS,
    PolicyViolation,
    redact_sensitive_text,
    truncate_output,
    validate_and_resolve_path,
)
from ops_lite.reader import is_binary_file

HARD_MAX_BATCH_OPS = 256
HARD_MAX_REPLACE_FILES = 100
HARD_MAX_REPLACEMENTS = 2000


def execute_batch_operations(
    action: str,  # "plan" | "run"
    operations: List[Dict[str, Any]],
    root: str = ".",
    base_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Plan or execute copy, move, and remove operations safely with preflight checks.
    """
    action_clean = action.strip().lower()
    if action_clean not in ("plan", "run"):
        return {"error": f"Invalid action '{action}'. Must be 'plan' or 'run'."}

    if not operations or len(operations) == 0:
        return {"error": "Operations list cannot be empty."}

    if len(operations) > HARD_MAX_BATCH_OPS:
        return {"error": f"Batch exceeds maximum limit of {HARD_MAX_BATCH_OPS} operations."}

    workspace = validate_and_resolve_path(root, base_root)
    plan_receipts: List[Dict[str, Any]] = []
    has_errors = False
    created_in_batch: set[str] = set()

    # Preflight phase
    for idx, item in enumerate(operations):
        op = item.get("op", "").lower()
        src_path_str = item.get("path")
        dest_path_str = item.get("to")

        receipt = {
            "index": idx + 1,
            "op": op,
            "path": src_path_str,
            "to": dest_path_str,
            "status": "ok",
            "message": "",
        }

        if op not in ("copy", "move", "remove"):
            receipt["status"] = "error"
            receipt["message"] = f"Unsupported op '{op}'. Must be 'copy', 'move', or 'remove'."
            has_errors = True
            plan_receipts.append(receipt)
            continue

        if not src_path_str:
            receipt["status"] = "error"
            receipt["message"] = "Source 'path' is required."
            has_errors = True
            plan_receipts.append(receipt)
            continue

        # Allow non-existent if the source will be produced by an earlier step in the batch
        norm_src = src_path_str.replace("\\", "/").lower()
        will_be_created = norm_src in created_in_batch

        # Validate source path
        try:
            src_resolved = validate_and_resolve_path(
                src_path_str, base_root=str(workspace), allow_non_existent=will_be_created
            )
            receipt["resolved_src"] = str(src_resolved)
        except Exception as e:
            receipt["status"] = "error"
            receipt["message"] = f"Source path validation failed: {e}"
            has_errors = True
            plan_receipts.append(receipt)
            continue

        # Validate destination for copy/move
        if op in ("copy", "move"):
            if not dest_path_str:
                receipt["status"] = "error"
                receipt["message"] = f"Destination 'to' is required for op '{op}'."
                has_errors = True
                plan_receipts.append(receipt)
                continue

            try:
                dest_resolved = validate_and_resolve_path(
                    dest_path_str, base_root=str(workspace), allow_non_existent=True
                )
                receipt["resolved_to"] = str(dest_resolved)
                created_in_batch.add(dest_path_str.replace("\\", "/").lower())
            except Exception as e:
                receipt["status"] = "error"
                receipt["message"] = f"Destination path validation failed: {e}"
                has_errors = True
                plan_receipts.append(receipt)
                continue

        plan_receipts.append(receipt)

    lines = [f"# Batch Operations ({action_clean.upper()}): {len(operations)} items"]
    if has_errors:
        lines.append("> [!WARNING] Preflight detected validation errors. Run will be blocked until resolved.")

    lines.append("| # | Op | Path | To | Status | Details |")
    lines.append("| - | -- | ---- | -- | ------ | ------- |")

    # If run and no preflight errors, execute
    executed_count = 0
    if action_clean == "run" and not has_errors:
        for r in plan_receipts:
            op = r["op"]
            src = Path(r["resolved_src"])
            try:
                if op == "remove":
                    if src.is_dir():
                        shutil.rmtree(src)
                    else:
                        src.unlink()
                    r["message"] = "Removed successfully."
                elif op == "copy":
                    dest = Path(r["resolved_to"])
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if src.is_dir():
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dest)
                    r["message"] = "Copied successfully."
                elif op == "move":
                    dest = Path(r["resolved_to"])
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest))
                    r["message"] = "Moved successfully."
                executed_count += 1
            except Exception as e:
                r["status"] = "failed"
                r["message"] = f"Execution failed: {e}"

    for r in plan_receipts:
        status_badge = f"`{r['status'].upper()}`"
        lines.append(
            f"| {r['index']} | `{r['op']}` | `{r['path']}` | `{r.get('to') or '-'}` | {status_badge} | {r['message']} |"
        )

    if action_clean == "plan":
        lines.append("\n> Preflight verified. Call with `action: 'run'` to execute.")

    return {
        "action": action_clean,
        "total": len(operations),
        "executed": executed_count,
        "has_errors": has_errors,
        "receipts": plan_receipts,
        "formatted": "\n".join(lines),
    }


def replace_literal_in_files(
    pattern: str,
    replacement: str,
    path: str = ".",
    glob: Optional[List[str]] = None,
    max_replacements: int = 50,
    dry_run: bool = True,
    base_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic literal text replacement across UTF-8 files with dryRun support.
    """
    if not pattern:
        return {"error": "Pattern cannot be empty", "formatted": "Error: Pattern cannot be empty"}

    root = validate_and_resolve_path(path, base_root)
    base = root if root.is_dir() else root.parent

    effective_max = min(max_replacements, HARD_MAX_REPLACEMENTS)

    files_to_check: List[Path] = []
    if root.is_file():
        files_to_check.append(root)
    else:
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            try:
                rel = entry.relative_to(base)
            except ValueError:
                continue

            if any(p in DEFAULT_IGNORED_DIRS for p in rel.parts[:-1]):
                continue

            rel_str = str(rel).replace("\\", "/")
            if glob:
                matched = False
                for g in glob:
                    norm_g = g.replace("\\", "/")
                    if fnmatch.fnmatch(rel_str, norm_g) or fnmatch.fnmatch(entry.name, norm_g):
                        matched = True
                        break
                if not matched:
                    continue

            files_to_check.append(entry)

    modified_files: List[Dict[str, Any]] = []
    total_replacements = 0

    for fpath in files_to_check:
        if len(modified_files) >= HARD_MAX_REPLACE_FILES or total_replacements >= effective_max:
            break

        if is_binary_file(fpath):
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        count = content.count(pattern)
        if count == 0:
            continue

        allowed_count = min(count, effective_max - total_replacements)
        new_content = content.replace(pattern, replacement, allowed_count)
        total_replacements += allowed_count

        rel_path_str = str(fpath.relative_to(base)).replace("\\", "/")
        modified_files.append({
            "path": rel_path_str,
            "occurrences": allowed_count,
        })

        if not dry_run:
            try:
                fpath.write_text(new_content, encoding="utf-8")
            except OSError as e:
                modified_files[-1]["error"] = str(e)

    lines = [
        f"# Replace Literal ({'DRY RUN' if dry_run else 'EXECUTED'})",
        f"- **Pattern**: `{pattern}`",
        f"- **Replacement**: `{replacement}`",
        f"- **Total Replaced**: {total_replacements}",
        f"- **Files Modified**: {len(modified_files)}",
    ]

    if modified_files:
        lines.append("\n| File | Replacements |")
        lines.append("| :--- | :--- |")
        for mf in modified_files:
            err = f" (Error: {mf['error']})" if "error" in mf else ""
            lines.append(f"| `{mf['path']}` | {mf['occurrences']}{err} |")

    if dry_run and total_replacements > 0:
        lines.append("\n> Preview only. Call with `dry_run: false` to apply changes.")

    return {
        "dry_run": dry_run,
        "total_replacements": total_replacements,
        "files_count": len(modified_files),
        "files": modified_files,
        "formatted": "\n".join(lines),
    }
