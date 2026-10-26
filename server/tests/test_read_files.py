import pytest
from pathlib import Path

from ops_lite.reader import clear_read_cache, read_file_bounded, read_files_batch


def test_read_files_batch_basic(tmp_path):
    f1 = tmp_path / "one.txt"
    f1.write_text("line_1\nline_2\nline_3\n", encoding="utf-8")
    f2 = tmp_path / "two.txt"
    f2.write_text("alpha\nbeta\n", encoding="utf-8")

    batch = [
        {"path": "one.txt", "start_line": 1, "end_line": 2},
        {"path": "two.txt", "start_line": 1, "end_line": 2},
    ]

    res = read_files_batch(batch, base_root=str(tmp_path), force=True)
    assert res["total_files"] == 2
    assert res["successful_count"] == 2
    assert "one.txt" in res["formatted"]
    assert "two.txt" in res["formatted"]
    assert "line_1" in res["formatted"]
    assert "alpha" in res["formatted"]


def test_read_files_batch_partial_failure_isolation(tmp_path):
    f1 = tmp_path / "exists.txt"
    f1.write_text("content", encoding="utf-8")

    batch = [
        {"path": "exists.txt"},
        {"path": "missing.txt"},
    ]

    res = read_files_batch(batch, base_root=str(tmp_path), force=True)
    assert res["total_files"] == 2
    assert res["successful_count"] == 1
    assert "exists.txt" in res["formatted"]
    assert "missing.txt" in res["formatted"]
    assert "Error:" in res["formatted"] or "Path does not exist" in res["formatted"]


def test_read_deduplication(tmp_path):
    clear_read_cache()
    sample = tmp_path / "memo.txt"
    sample.write_text("fixed content", encoding="utf-8")

    # First read
    res1 = read_file_bounded(str(sample), base_root=str(tmp_path), start_line=1, end_line=1)
    assert not res1["is_deduplicated"]
    assert "fixed content" in res1["content"]

    # Second read: deduplicated!
    res2 = read_file_bounded(str(sample), base_root=str(tmp_path), start_line=1, end_line=1)
    assert res2["is_deduplicated"] is True
    assert "Deduplicated" in res2["content"]

    # Force read: bypasses deduplication
    res3 = read_file_bounded(str(sample), base_root=str(tmp_path), start_line=1, end_line=1, force=True)
    assert not res3["is_deduplicated"]
    assert "fixed content" in res3["content"]
