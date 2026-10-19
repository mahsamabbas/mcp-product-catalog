from fastapi import APIRouter, HTTPException, Request

from app.catalog.db import connect
from app.chat import ChatServiceError
from app.schemas import CatalogSummary, ChatRequest, ChatResponse, HealthResponse

router = APIRouter()


def _catalog_snapshot(db_path: str) -> tuple[int, dict[str, int], list[str]]:
    conn = connect(db_path)
    try:
        product_count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE active = 1"
        ).fetchone()[0]
        category_rows = conn.execute(
            """
            SELECT category, COUNT(*) AS product_count
            FROM products
            WHERE active = 1
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()
        sku_rows = conn.execute(
            """
            SELECT sku
            FROM products
            WHERE active = 1
            ORDER BY sku
            LIMIT 3
            """
        ).fetchall()
    finally:
        conn.close()

    categories = {row["category"]: row["product_count"] for row in category_rows}
    sample_skus = [row["sku"] for row in sku_rows]
    return product_count, categories, sample_skus


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    state = request.app.state
    product_count, _, _ = _catalog_snapshot(state["catalog_db_path"])
    return HealthResponse(
        ollama=await state["ollama"].healthy(),
        mcp=state["mcp"].ready,
        catalog_count=product_count,
    )


@router.get("/catalog/summary", response_model=CatalogSummary)
async def catalog_summary(request: Request) -> CatalogSummary:
    product_count, categories, sample_skus = _catalog_snapshot(
        request.app.state["catalog_db_path"]
    )
    return CatalogSummary(
        product_count=product_count,
        categories=categories,
        sample_skus=sample_skus,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    state = request.app.state
    settings = state["settings"]
    try:
        return await state["run_chat"](
            message=body.message,
            history=body.history,
            mcp=state["mcp"],
            ollama=state["ollama"],
            max_rounds=settings.max_tool_rounds,
            model=settings.ollama_chat_model,
        )
    except ChatServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc
