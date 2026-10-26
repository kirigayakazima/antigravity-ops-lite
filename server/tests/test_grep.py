import pytest
from pathlib import Path

from ops_lite.grep import glob_files, grep_workspace


def test_glob_files_basic(tmp_path):
    (tmp_path / "a.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "b.txt").write_text("text", encoding="utf-8")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "c.py").write_text("print(2)", encoding="utf-8")

    res = glob_files(path=str(tmp_path), patterns=["**/*.py"], base_root=str(tmp_path))
    assert res["total"] == 2
    paths = [it["path"] for it in res["items"]]
    assert "a.py" in paths
    assert "subdir/c.py" in paths or "subdir\\c.py" in paths


def test_glob_files_negative_patterns(tmp_path):
    (tmp_path / "app.py").write_text("code", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("test", encoding="utf-8")

    res = glob_files(path=str(tmp_path), patterns=["**/*.py", "!tests/**"], base_root=str(tmp_path))
    assert res["total"] == 1
    assert "app.py" in res["items"][0]["path"]


def test_grep_output_modes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "one.py").write_text("def find_me():\n    pass\n", encoding="utf-8")
    (src / "two.py").write_text("find_me()\nfind_me()\n", encoding="utf-8")

    # Mode: content
    res_content = grep_workspace(pattern="find_me", path=str(src), output_mode="content", base_root=str(tmp_path))
    assert res_content["total_matches"] == 3
    assert "one.py" in res_content["formatted"]
    assert "two.py" in res_content["formatted"]

    # Mode: files_with_matches
    res_files = grep_workspace(pattern="find_me", path=str(src), output_mode="files_with_matches", base_root=str(tmp_path))
    assert "one.py" in res_files["formatted"]
    assert "two.py" in res_files["formatted"]

    # Mode: count
    res_count = grep_workspace(pattern="find_me", path=str(src), output_mode="count", base_root=str(tmp_path))
    assert ": 1" in res_count["formatted"]
    assert ": 2" in res_count["formatted"]

    # Mode: summary
    res_summary = grep_workspace(pattern="find_me", path=str(src), output_mode="summary", base_root=str(tmp_path))
    assert "**Total Matches**: 3" in res_summary["formatted"]
    assert "**Matching Files**: 2" in res_summary["formatted"]


def test_grep_invalid_regex(tmp_path):
    res = grep_workspace(pattern="[unclosed", path=str(tmp_path), base_root=str(tmp_path))
    assert "Invalid regular expression" in res["formatted"]
