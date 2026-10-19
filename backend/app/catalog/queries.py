import sqlite3


def _clamp_limit(limit: int) -> int:
    if limit < 1:
        return 5
    return min(limit, 20)


def search_products(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    lim = _clamp_limit(limit)
    like = f"%{q}%"
    rows = conn.execute(
        """
        SELECT sku, name, category, price, currency, short_description
        FROM products
        WHERE active = 1
          AND (
            name LIKE ? COLLATE NOCASE
            OR category LIKE ? COLLATE NOCASE
            OR short_description LIKE ? COLLATE NOCASE
            OR sku LIKE ? COLLATE NOCASE
          )
        ORDER BY name
        LIMIT ?
        """,
        (like, like, like, like, lim),
    ).fetchall()
    return [dict(r) for r in rows]


def lookup_stock(conn: sqlite3.Connection, sku: str) -> dict:
    key = (sku or "").strip()
    if not key:
        return {"sku": key, "found": False}
    row = conn.execute(
        """
        SELECT sku, name, quantity, warehouse
        FROM products
        WHERE sku = ? AND active = 1
        """,
        (key,),
    ).fetchone()
    if row is None:
        return {"sku": key, "found": False}
    qty = int(row["quantity"])
    return {
        "sku": row["sku"],
        "name": row["name"],
        "found": True,
        "in_stock": qty > 0,
        "quantity": qty,
        "warehouse": row["warehouse"],
    }
