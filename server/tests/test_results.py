import pytest
from pathlib import Path

from ops_lite.policy import PolicyViolation
from ops_lite.results import ResultStore


def test_result_store_pagination(tmp_path):
    store = ResultStore(store_dir=tmp_path)
    lines = [f"Item {i}" for i in range(50)]
    
    res_id = store.store(result_type="test", summary="Test batch", items=lines)
    assert res_id.startswith("res_")

    # First page
    page1 = store.retrieve(res_id, offset=0, limit=10)
    assert page1["total_items"] == 50
    assert len(page1["items"]) == 10
    assert page1["has_more"] is True
    assert page1["items"][0] == "Item 0"

    # Second page
    page2 = store.retrieve(res_id, offset=10, limit=10)
    assert len(page2["items"]) == 10
    assert page2["items"][0] == "Item 10"


def test_result_store_invalid_id(tmp_path):
    store = ResultStore(store_dir=tmp_path)
    with pytest.raises(PolicyViolation):
        store.retrieve("../../etc/passwd")


def test_result_store_not_found(tmp_path):
    store = ResultStore(store_dir=tmp_path)
    res = store.retrieve("res_0000000000000000")
    assert res["status"] == "not_found"
