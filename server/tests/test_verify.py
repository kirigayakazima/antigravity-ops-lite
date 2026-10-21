import json
from pathlib import Path
from ops_lite.verify import detect_check_command, run_verification_suite


def test_detect_check_command_node(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"scripts": {"test": "mocha", "build": "webpack"}}), encoding="utf-8")
    
    test_cmd = detect_check_command(tmp_path, "test")
    assert test_cmd == ["npm", "test"]

    build_cmd = detect_check_command(tmp_path, "build")
    assert build_cmd == ["npm", "run", "build"]


def test_detect_check_command_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    
    test_cmd = detect_check_command(tmp_path, "test")
    assert test_cmd == ["python", "-m", "pytest"]


def test_run_verification_suite_not_configured(tmp_path):
    res = run_verification_suite(path=str(tmp_path), base_root=str(tmp_path), checks=["test"])
    assert res["status"] == "not_configured"
    assert res["counts"]["not_configured"] == 1
