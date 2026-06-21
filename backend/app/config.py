"""Application settings (api-websocket.md §2.2).

Process-wide config — CORS origins, seed paths, the default demo asker, top_k, and the
three Claude model ids. Read once at startup via `get_settings()` and stashed in app.state.

Implementation note: this uses a stdlib dataclass + a manual `.env` loader rather than
`pydantic-settings`. The installed `pydantic 2.5.0` is incompatible with the installed
`pydantic-settings` (it imports a newer pydantic internal), and the codebase already
prefers a dependency-free `.env` loader (see app/claude/client.py). Same env semantics:
RELAY_-prefixed overrides, loaded from backend/.env in dev.
"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional


def _load_env_file() -> None:
    """Populate process env from backend/.env (without overriding already-set vars).
    Mirrors app/claude/client.py — avoids a hard dependency on python-dotenv."""
    env_path = pathlib.Path(__file__).resolve().parents[1] / ".env"   # backend/.env
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


@dataclass
class Settings:
    """Process-wide settings. Defaults below; env overrides applied in get_settings()."""

    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    agents_path: str = "app/data/agents.json"
    corpora_dir: str = "app/data/corpora"
    default_asker: str = "agent_you"        # the "You" node (not a party) -> all 3 parties respond
    top_k: int = 5                          # passed to search(); small for low verify latency

    # Claude model ids (BUILD_INDEX.md §2.1 model-id note / OQ-6).
    model_redaction: str = "claude-opus-4-8"
    model_verification: str = "claude-opus-4-8"   # sanctioned downgrade: claude-haiku-4-5
    model_synthesis: str = "claude-opus-4-8"

    # Search backend dispatch: "stub" until H8, then "cosine"/"hybrid".
    relay_search: str = "stub"

    anthropic_api_key: Optional[str] = None    # from env ANTHROPIC_API_KEY


@lru_cache
def get_settings() -> Settings:
    """Return the cached process-wide Settings instance, with env overrides applied.

    Overridable via RELAY_SEARCH / RELAY_DEFAULT_ASKER / RELAY_TOP_K (the same vars the
    responder + search modules already read). The ANTHROPIC_API_KEY is also loaded
    independently by app.claude.client, so synthesis works regardless of this field.
    """
    _load_env_file()
    s = Settings()
    s.relay_search = os.environ.get("RELAY_SEARCH", s.relay_search)
    s.default_asker = os.environ.get("RELAY_DEFAULT_ASKER", s.default_asker)
    if os.environ.get("RELAY_TOP_K"):
        s.top_k = int(os.environ["RELAY_TOP_K"])
    s.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", s.anthropic_api_key)
    return s
