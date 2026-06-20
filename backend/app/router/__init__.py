"""Router subsystem: in-process fan-out + live-event timing (router.md).

Re-exports: Router, build_default_registry, event builders. The fan-out engine and
the event clock — emits all `agent-activated` before any responder is awaited, then
concurrent responder calls, emitting one `response-item` per resolved item. Makes
ZERO Claude calls and decides NO gate verdicts; it calls into the responder pipeline.
"""
from __future__ import annotations

from app.router.router import Router  # noqa: F401
from app.router.events import agent_activated_event, response_item_event  # noqa: F401
from app.agents.registry import build_registry as build_default_registry  # noqa: F401

__all__ = [
    "Router",
    "build_default_registry",
    "agent_activated_event",
    "response_item_event",
]
