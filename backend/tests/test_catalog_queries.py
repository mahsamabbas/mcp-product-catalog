import sqlite3
from pathlib import Path

from app.catalog.db import connect, init_db
from app.catalog.queries import lookup_stock, search_products


def _conn(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "test.db"
    init_db(str(db))
    return connect(str(db))


def test_search_finds_earbuds(tmp_path: Path):
    conn = _conn(tmp_path)
    rows = search_products(conn, "earbuds", limit=5)
    assert len(rows) >= 1
    assert all("sku" in r and "price" in r for r in rows)
    assert any("earbud" in r["name"].lower() or "earbud" in r["short_description"].lower() for r in rows)


def test_search_multi_word_terms_are_anded_across_fields(tmp_path: Path):
    conn = _conn(tmp_path)

    rows = search_products(conn, "AeroSound headphones", limit=5)

    assert [row["sku"] for row in rows] == ["CP-1001"]
    assert search_products(conn, "AeroSound laptops", limit=5) == []


def test_search_empty_query_returns_empty(tmp_path: Path):
    conn = _conn(tmp_path)
    assert search_products(conn, "   ", limit=5) == []


def test_search_no_match(tmp_path: Path):
    conn = _conn(tmp_path)
    assert search_products(conn, "zzzz-no-such-product-qqq", limit=5) == []


def test_lookup_stock_hit(tmp_path: Path):
    conn = _conn(tmp_path)
    hit = search_products(conn, "laptop", limit=1)[0]
    stock = lookup_stock(conn, hit["sku"])
    assert stock["found"] is True
    assert stock["sku"] == hit["sku"]
    assert "quantity" in stock and "in_stock" in stock
    assert stock["in_stock"] == (stock["quantity"] > 0)


def test_lookup_stock_miss(tmp_path: Path):
    conn = _conn(tmp_path)
    stock = lookup_stock(conn, "SKU-DOES-NOT-EXIST")
    assert stock == {"sku": "SKU-DOES-NOT-EXIST", "found": False}


def test_limit_capped_at_20(tmp_path: Path):
    conn = _conn(tmp_path)
    rows = search_products(conn, "a", limit=100)
    assert len(rows) <= 20
