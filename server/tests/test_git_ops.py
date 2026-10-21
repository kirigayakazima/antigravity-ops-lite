import subprocess
from pathlib import Path
from ops_lite.git_ops import get_git_summary


def test_git_summary_non_git_dir(tmp_path):
    res = get_git_summary(path=str(tmp_path), base_root=str(tmp_path))
    assert res["is_git"] is False
    assert "not_a_git_repository" in res["status"]


def test_git_summary_with_git_repo(tmp_path):
    # Initialize a temporary git repository
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)

    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello Git", encoding="utf-8")
    
    res = get_git_summary(path=str(tmp_path), base_root=str(tmp_path))
    assert res["is_git"] is True
    assert res["untracked_count"] == 1
