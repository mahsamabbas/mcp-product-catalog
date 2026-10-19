from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def non_empty(cls, value: str) -> str:
        message = (value or "").strip()
        if not message:
            raise ValueError("message must not be empty")
        return message


class ToolTraceEvent(BaseModel):
    name: str
    args: dict[str, Any]
    result: Any
    ms: int
    ok: bool
    error: str | None = None


class ChatResponse(BaseModel):
    answer: str
    tool_trace: list[ToolTraceEvent]


class HealthResponse(BaseModel):
    ollama: bool
    mcp: bool
    catalog_count: int | None = None


class CatalogSummary(BaseModel):
    product_count: int
    categories: dict[str, int]
    sample_skus: list[str]
