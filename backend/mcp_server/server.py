from __future__ import annotations

import json
import os

from mcp.server.mcpserver import MCPServer

from app.catalog import queries as catalog
from app.catalog.db import connect, init_db

DB_PATH = os.environ.get("CATALOG_DB_PATH", "./data/catalog.db")
init_db(DB_PATH)

mcp = MCPServer("catalogpilot")


@mcp.tool(name="search_products")
def search_products(query: str, limit: int = 5) -> str:
    """Search the electronics catalog by name, category, description, or SKU."""
    conn = connect(DB_PATH)
    try:
        rows = catalog.search_products(conn, query, limit=limit)
        return json.dumps({"results": rows, "count": len(rows)})
    finally:
        conn.close()


@mcp.tool(name="lookup_stock")
def lookup_stock(sku: str) -> str:
    """Look up stock quantity and warehouse for a product SKU."""
    conn = connect(DB_PATH)
    try:
        return json.dumps(catalog.lookup_stock(conn, sku))
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
