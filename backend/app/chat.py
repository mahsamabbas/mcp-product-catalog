from __future__ import annotations

import json
from typing import Any

from app.config import Settings
from app.schemas import ChatResponse, HistoryMessage, ToolTraceEvent

SYSTEM_PROMPT = """You are CatalogPilot, a product catalog assistant for a synthetic consumer-electronics store.
Use tools for ANY product, price, stock, or SKU fact. Never invent catalog data.
If tools return empty or not found, say so honestly.
Refuse purchases, carts, payments, and requests for personal data.
Greetings and capability questions may be answered without tools.
Keep answers concise."""


class ChatServiceError(RuntimeError):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status
        self.status_code = status


def to_ollama_tools(mcp_tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description") or tool["name"],
                "parameters": tool.get("input_schema")
                or {"type": "object", "properties": {}},
            },
        }
        for tool in mcp_tools
    ]


async def run_chat(
    message: str,
    history: list[HistoryMessage],
    mcp: Any,
    ollama: Any,
    settings: Settings | None = None,
    *,
    max_rounds: int | None = None,
    model: str | None = None,
) -> ChatResponse:
    if max_rounds is None:
        max_rounds = settings.max_tool_rounds if settings else 5
    if model is None:
        model = settings.ollama_chat_model if settings else "qwen2.5:7b"

    if not mcp.ready:
        raise ChatServiceError("Tool layer unavailable", status=503)

    try:
        tools = to_ollama_tools(await mcp.list_tools())
    except Exception as exc:
        raise ChatServiceError("Tool layer unavailable", status=503) from exc

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(item.model_dump() for item in history),
        {"role": "user", "content": message},
    ]
    trace: list[ToolTraceEvent] = []

    for _ in range(max_rounds):
        if not mcp.ready:
            raise ChatServiceError("Tool layer unavailable", status=503)
        try:
            response = await ollama.chat(messages=messages, tools=tools, model=model)
        except Exception as exc:
            raise ChatServiceError("Answer service unavailable", status=503) from exc
        if not mcp.ready:
            raise ChatServiceError("Tool layer unavailable", status=503)

        assistant = response.get("message") or {}
        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls:
            return ChatResponse(
                answer=str(assistant.get("content") or ""),
                tool_trace=trace,
            )

        messages.append(assistant)
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            name = str(function.get("name") or "")
            arguments, parse_error = _parse_arguments(function.get("arguments"))
            if parse_error:
                result, elapsed_ms, ok, error = None, 0, False, parse_error
            else:
                if not mcp.ready:
                    raise ChatServiceError("Tool layer unavailable", status=503)
                result, elapsed_ms, ok, error = await mcp.call_tool(name, arguments)
                if not mcp.ready:
                    raise ChatServiceError("Tool layer unavailable", status=503)

            trace.append(
                ToolTraceEvent(
                    name=name,
                    args=arguments,
                    result=result,
                    ms=elapsed_ms,
                    ok=ok,
                    error=error,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(
                        result if ok else {"error": error},
                        ensure_ascii=False,
                        default=str,
                    ),
                }
            )

    return ChatResponse(
        answer="Sorry, I couldn't complete that catalog request within the tool limit.",
        tool_trace=trace,
    )


def _parse_arguments(value: Any) -> tuple[dict[str, Any], str | None]:
    if isinstance(value, dict):
        return value, None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}, "Tool arguments were not valid JSON"
        if isinstance(parsed, dict):
            return parsed, None
    return {}, "Tool arguments must be a JSON object"
