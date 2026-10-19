from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from time import perf_counter
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpSessionManager:
    def __init__(
        self,
        catalog_db_path: str = "./data/catalog.db",
        server_script: str = "mcp_server/server.py",
        *,
        session: Any | None = None,
    ) -> None:
        self._backend_dir = Path(__file__).resolve().parents[1]
        self._catalog_db_path = catalog_db_path
        self._server_script = server_script
        self._session = session
        self._injected_session = session is not None
        self._stack: AsyncExitStack | None = None
        self._ok = False

    @property
    def ready(self) -> bool:
        return self._ok and self._session is not None

    async def start(self) -> None:
        if self.ready:
            return

        if self._injected_session:
            await self._session.initialize()
            self._ok = True
            return

        stack = AsyncExitStack()
        try:
            script_path = Path(self._server_script)
            if not script_path.is_absolute():
                script_path = self._backend_dir / script_path

            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = os.pathsep.join(
                part
                for part in (str(self._backend_dir), existing_pythonpath)
                if part
            )
            env["CATALOG_DB_PATH"] = self._catalog_db_path

            parameters = StdioServerParameters(
                command=sys.executable,
                args=[str(script_path)],
                env=env,
                cwd=self._backend_dir,
            )
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(parameters)
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
        except BaseException:
            await stack.aclose()
            raise

        self._stack = stack
        self._session = session
        self._ok = True

    async def stop(self) -> None:
        self._ok = False
        stack, self._stack = self._stack, None
        try:
            if stack is not None:
                await stack.aclose()
        finally:
            if not self._injected_session:
                self._session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        session = self._require_session()
        response = await session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in response.tools
        ]

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> tuple[Any, int, bool, str | None]:
        started = perf_counter()
        try:
            session = self._require_session()
            response = await session.call_tool(name, arguments)
            result = self._parse_tool_result(response)
            ok = not response.is_error
            error = None if ok else self._error_message(result)
            return result, self._elapsed_ms(started), ok, error
        except Exception as exc:
            if self._is_transport_error(exc):
                self._ok = False
            return None, self._elapsed_ms(started), False, str(exc)

    def _require_session(self) -> Any:
        if not self.ready:
            raise RuntimeError("MCP session is not started")
        return self._session

    @staticmethod
    def _parse_tool_result(response: Any) -> Any:
        structured = response.structured_content
        if isinstance(structured, dict) and set(structured) == {"result"}:
            wrapped = structured["result"]
            if isinstance(wrapped, str):
                try:
                    return json.loads(wrapped)
                except json.JSONDecodeError:
                    return wrapped
        if structured is not None:
            return structured

        text_parts = [
            item.text
            for item in response.content
            if getattr(item, "type", None) == "text"
        ]
        if len(text_parts) == 1:
            try:
                return json.loads(text_parts[0])
            except json.JSONDecodeError:
                return text_parts[0]
        if text_parts:
            return "\n".join(text_parts)
        return [
            item.model_dump(mode="json", by_alias=True, exclude_none=True)
            for item in response.content
        ]

    @staticmethod
    def _error_message(result: Any) -> str:
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))

    @staticmethod
    def _is_transport_error(exc: Exception) -> bool:
        transport_types = {
            "BrokenResourceError",
            "ClosedResourceError",
            "EndOfStream",
        }
        current: BaseException | None = exc
        while current is not None:
            if isinstance(current, (BrokenPipeError, ConnectionError, EOFError)):
                return True
            if type(current).__name__ in transport_types:
                return True
            message = str(current).lower()
            if any(
                marker in message
                for marker in (
                    "broken pipe",
                    "closed session",
                    "connection closed",
                    "connection lost",
                    "session is closed",
                    "stream is closed",
                )
            ):
                return True
            current = current.__cause__ or current.__context__
        return False
