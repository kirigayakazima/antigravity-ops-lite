import pytest
from pathlib import Path

from ops_lite.search import search_workspace


def test_search_workspace_basic(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    f1 = src / "hello.py"
    f1.write_text("def hello():\n    target_symbol = 42\n    return target_symbol\n", encoding="utf-8")
    
    f2 = src / "other.py"
    f2.write_text("nothing here\n", encoding="utf-8")

    res = search_workspace(
        query="target_symbol",
        path=str(src),
        base_root=str(tmp_path),
        context_lines=1,
    )
    assert res["total_matches"] == 2
    assert res["matches_returned"] == 2
    assert "hello.py" in res["output"]
    assert "target_symbol" in res["output"]


def test_search_workspace_excludes(tmp_path):
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "pkg.js").write_text("const target = 1;", encoding="utf-8")

    src = tmp_path / "src"
    src.mkdir()
    (src / "app.js").write_text("const target = 2;", encoding="utf-8")

    res = search_workspace(
        query="target",
        path=str(tmp_path),
        base_root=str(tmp_path),
    )
    # node_modules should be ignored by default
    assert "node_modules" not in res["output"]
    assert "src/app.js" in res["output"]
