import sqlite3
from pathlib import Path

from app.catalog.seed_data import PRODUCTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price REAL NOT NULL,
  currency TEXT NOT NULL,
  short_description TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  warehouse TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);
"""


def init_db(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO products
                (sku, name, category, price, currency, short_description, quantity, warehouse, active)
                VALUES (:sku, :name, :category, :price, :currency, :short_description, :quantity, :warehouse, :active)
                """,
                PRODUCTS,
            )
            conn.commit()
    finally:
        conn.close()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
