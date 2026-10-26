import pytest
from pathlib import Path

from ops_lite.batch import execute_batch_operations, replace_literal_in_files


def test_batch_operations_plan_and_run(tmp_path):
    f1 = tmp_path / "origin.txt"
    f1.write_text("hello", encoding="utf-8")

    ops = [
        {"op": "copy", "path": "origin.txt", "to": "copied.txt"},
        {"op": "move", "path": "copied.txt", "to": "moved.txt"},
    ]

    # Plan
    plan_res = execute_batch_operations("plan", ops, root=str(tmp_path), base_root=str(tmp_path))
    assert not plan_res["has_errors"]
    assert "PLAN" in plan_res["formatted"]
    assert not (tmp_path / "moved.txt").exists()

    # Run copy
    run_copy = execute_batch_operations(
        "run",
        [{"op": "copy", "path": "origin.txt", "to": "copied.txt"}],
        root=str(tmp_path),
        base_root=str(tmp_path),
    )
    assert run_copy["executed"] == 1
    assert (tmp_path / "copied.txt").exists()

    # Run remove
    run_remove = execute_batch_operations(
        "run",
        [{"op": "remove", "path": "copied.txt"}],
        root=str(tmp_path),
        base_root=str(tmp_path),
    )
    assert run_remove["executed"] == 1
    assert not (tmp_path / "copied.txt").exists()


def test_batch_operations_preflight_error(tmp_path):
    ops = [
        {"op": "copy", "path": "nonexistent.txt", "to": "dest.txt"},
        {"op": "invalid_op", "path": "origin.txt"},
    ]
    res = execute_batch_operations("plan", ops, root=str(tmp_path), base_root=str(tmp_path))
    assert res["has_errors"] is True


def test_replace_literal_in_files(tmp_path):
    f1 = tmp_path / "a.py"
    f1.write_text("old_function() and old_function()", encoding="utf-8")
    f2 = tmp_path / "b.py"
    f2.write_text("old_function()", encoding="utf-8")

    # Dry run
    res_dry = replace_literal_in_files(
        pattern="old_function",
        replacement="new_function",
        path=str(tmp_path),
        dry_run=True,
        base_root=str(tmp_path),
    )
    assert res_dry["total_replacements"] == 3
    assert res_dry["files_count"] == 2
    # Verify file content is unchanged
    assert "old_function" in f1.read_text(encoding="utf-8")

    # Real run
    res_run = replace_literal_in_files(
        pattern="old_function",
        replacement="new_function",
        path=str(tmp_path),
        dry_run=False,
        base_root=str(tmp_path),
    )
    assert res_run["total_replacements"] == 3
    assert "new_function() and new_function()" in f1.read_text(encoding="utf-8")
    assert "new_function()" in f2.read_text(encoding="utf-8")
