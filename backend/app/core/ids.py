"""query_id minting (api-websocket.md §2.4, BUILD_INDEX.md §2 core/ids.py).

Responsibility: mint the opaque correlation id that ties all WS events for one run
together. Contract example shape: "q_8f3a2c". This is a SKELETON — no logic.
"""
from __future__ import annotations

import uuid


def new_query_id() -> str:
    """Return a fresh opaque query id: 'q_' + 6 hex (contract example "q_8f3a2c")."""
    return "q_" + uuid.uuid4().hex[:6]
