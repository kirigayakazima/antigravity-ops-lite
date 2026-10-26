import pytest
from pathlib import Path

from ops_lite.policy import PolicyViolation
from ops_lite.table import read_table_bounded


def test_read_table_csv(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("id,name,role\n1,Alice,Engineer\n2,Bob,Designer\n3,Charlie,Product\n", encoding="utf-8")

    res = read_table_bounded(str(csv_file), offset=1, limit=2, base_root=str(tmp_path))
    assert res["total_rows"] == 3
    assert "| id | name | role |" in res["formatted"]
    assert "| 1 | Alice | Engineer |" in res["formatted"]
    assert "| 2 | Bob | Designer |" in res["formatted"]
    assert "Charlie" not in res["formatted"]  # limit is 2
    assert res["has_more"] is True


def test_read_table_tsv(tmp_path):
    tsv_file = tmp_path / "data.tsv"
    tsv_file.write_text("colA\tcolB\nval1\tval2\n", encoding="utf-8")

    res = read_table_bounded(str(tsv_file), base_root=str(tmp_path))
    assert res["total_rows"] == 1
    assert "| colA | colB |" in res["formatted"]
    assert "| 1 | val1 | val2 |" in res["formatted"]


def test_read_table_binary_denied(tmp_path):
    bin_file = tmp_path / "data.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03")

    with pytest.raises(PolicyViolation):
        read_table_bounded(str(bin_file), base_root=str(tmp_path))
