from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    cors_origins: str = "http://localhost:3009"
    catalog_db_path: str = "./data/catalog.db"
    mcp_server_script: str = "mcp_server/server.py"
    max_tool_rounds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
