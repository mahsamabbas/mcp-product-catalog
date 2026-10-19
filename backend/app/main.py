from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.catalog.db import init_db
from app.chat import run_chat
from app.config import Settings, get_settings
from app.mcp_client import McpSessionManager
from app.ollama_client import OllamaClient
from app.routes import router

logger = logging.getLogger(__name__)


class AppState(dict[str, Any]):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class _TestingMcp:
    ready = False


class _TestingOllama:
    async def healthy(self) -> bool:
        return False


def _cors_origins(settings: Settings) -> list[str]:
    return [
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]


def create_app(testing: bool = False) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if testing:
            yield
            return

        init_db(settings.catalog_db_path)
        mcp = McpSessionManager(
            catalog_db_path=settings.catalog_db_path,
            server_script=settings.mcp_server_script,
        )
        app.state["mcp"] = mcp
        app.state["ollama"] = OllamaClient(settings.ollama_base_url)
        try:
            await mcp.start()
        except Exception:
            logger.exception("Failed to start MCP session")
        try:
            yield
        finally:
            await mcp.stop()

    app = FastAPI(lifespan=lifespan)
    app.state = AppState(
        settings=settings,
        catalog_db_path=settings.catalog_db_path,
        run_chat=run_chat,
        mcp=_TestingMcp(),
        ollama=_TestingOllama(),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
