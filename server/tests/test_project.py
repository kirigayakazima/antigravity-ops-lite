import json
from pathlib import Path

from ops_lite.project import detect_project_type, summarize_project


def test_detect_project_type_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    info = detect_project_type(tmp_path)
    assert any("Python" in t for t in info["project_types"])
    assert "pyproject.toml" in info["manifests"]


def test_detect_project_type_node(tmp_path):
    pkg_data = {"name": "test-node", "scripts": {"test": "jest", "build": "tsc"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg_data), encoding="utf-8")
    info = detect_project_type(tmp_path)
    assert any("Node.js" in t for t in info["project_types"])
    assert "npm" in info["scripts"]
    assert info["scripts"]["npm"]["test"] == "jest"


def test_summarize_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hi')", encoding="utf-8")

    res = summarize_project(path=str(tmp_path), base_root=str(tmp_path))
    assert "formatted" in res
    assert "pyproject.toml" in res["formatted"]
    assert "src/" in res["formatted"]
