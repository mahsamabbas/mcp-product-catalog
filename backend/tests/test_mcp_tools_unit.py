import json
from pathlib import Path

from app.catalog.db import init_db, connect
from app.catalog.queries import lookup_stock, search_products


def test_tool_payloads_json_serializable(tmp_path: Path):
    path = str(tmp_path / "c.db")
    init_db(path)
    conn = connect(path)
    results = search_products(conn, "cable", limit=3)
    assert json.dumps(results)
    miss = lookup_stock(conn, "NOPE")
    assert json.dumps(miss)
