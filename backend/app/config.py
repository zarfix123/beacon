"""Application settings (api-websocket.md §2.2).

Responsibility: pydantic-settings-backed config — CORS origins, seed paths, the
default demo asker, top_k, and the three Claude model ids. Read once at startup via
`get_settings()` and stashed in app.state. This is a SKELETON — no logic.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Process-wide settings. Env-prefixed `RELAY_`, loaded from `.env` in dev."""

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    agents_path: str = "app/data/agents.json"
    corpora_dir: str = "app/data/corpora"
    default_asker: str = "agent_helios"     # OQ-1: locked demo asker (clean 2-party fan-out)
    top_k: int = 5                          # passed to search(); small for low verify latency

    # Claude model ids (BUILD_INDEX.md §2.1 model-id note / OQ-6).
    model_redaction: str = "claude-opus-4-8"
    model_verification: str = "claude-opus-4-8"   # sanctioned downgrade: claude-haiku-4-5
    model_synthesis: str = "claude-opus-4-8"

    # Search backend dispatch: "stub" until H8, then "cosine".
    relay_search: str = "stub"

    anthropic_api_key: str | None = None    # from env ANTHROPIC_API_KEY

    class Config:
        env_prefix = "RELAY_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    """Return the cached process-wide Settings instance."""
    raise NotImplementedError("get_settings is a skeleton stub")
