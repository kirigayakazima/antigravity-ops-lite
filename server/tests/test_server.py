import pytest
from ops_lite.server import ops_summary, ops_search, ops_read, ops_run, ops_result


def test_ops_summary_tool():
    res = ops_summary(path=".")
    assert "Project Summary" in res or "Structure" in res


def test_ops_read_tool():
    # Read server pyproject.toml
    res = ops_read(path="server/pyproject.toml", start_line=1, end_line=5)
    assert "pyproject.toml" in res
    assert "File:" in res


def test_ops_search_tool():
    res = ops_search(query="MCPServer", path="server/ops_lite")
    assert "Search Results" in res
    assert "MCPServer" in res


def test_ops_run_unsupported_task():
    res = ops_run(task="rm_rf_everything")
    assert "Error: Unsupported task" in res


def test_ops_result_not_found():
    res = ops_result(result_id="res_1111222233334444")
    assert "Error:" in res or "not found" in res
