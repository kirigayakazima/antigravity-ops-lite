import pytest
from pathlib import Path

from ops_lite.policy import PolicyViolation
from ops_lite.reader import compute_file_hash, is_binary_file, read_file_bounded


def test_read_file_bounded_normal(tmp_path):
    sample = tmp_path / "code.py"
    sample.write_text("\n".join([f"line_{i}" for i in range(1, 21)]), encoding="utf-8")

    res = read_file_bounded(
        str(sample),
        base_root=str(tmp_path),
        start_line=5,
        end_line=10,
    )
    assert res["start_line"] == 5
    assert res["end_line"] == 10
    assert res["total_lines"] == 20
    assert "line_5" in res["content"]
    assert "line_10" in res["content"]
    assert "line_11" not in res["content"]
    assert res["has_more_lines"] is True
    assert res["next_start_line"] == 11
    assert len(res["file_hash"]) == 16


def test_read_file_bounded_binary_denied(tmp_path):
    bin_file = tmp_path / "binary.dat"
    bin_file.write_bytes(b"\x00\x01\x02\x03\xff")

    with pytest.raises(PolicyViolation, match="Cannot read binary file"):
        read_file_bounded(str(bin_file), base_root=str(tmp_path))


def test_read_file_bounded_directory_denied(tmp_path):
    sub_dir = tmp_path / "folder"
    sub_dir.mkdir()

    with pytest.raises(PolicyViolation, match="Target path is not a regular file"):
        read_file_bounded(str(sub_dir), base_root=str(tmp_path))
