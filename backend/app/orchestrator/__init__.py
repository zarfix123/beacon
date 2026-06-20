"""Orchestrator subsystem: the coordination core in the asking agent.

See backend/docs/orchestrator.md. Owns plan -> fan out (via router) -> collect ->
verify full -> synthesize -> emit one done. Re-exports the Orchestrator class.
"""
from __future__ import annotations

from app.orchestrator.orchestrator import Orchestrator  # noqa: F401

__all__ = ["Orchestrator"]
