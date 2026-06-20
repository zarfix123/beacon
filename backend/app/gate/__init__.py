"""Permission gate subsystem — wedge piece 1 (permission-gate.md §2.6).

Public surface: evaluate(), GatedResult, GateDecision, GateError, issue_grant +
capability types. Per-chunk policy check keyed off chunk.visibility that runs INSIDE
the responding agent, BEFORE any content crosses the boundary, mapping
public->full / restricted->redacted / private->denied. The redaction Claude call
itself lives in app/claude/redaction.py (BUILD_INDEX.md §2.1); the gate CALLS it.
"""
from __future__ import annotations

# Re-exports form the package's public surface. Imports are intentional even in the
# skeleton so call sites can be written against the stable surface.
from app.gate.gate import evaluate, GateError, PartyNameResolver  # noqa: F401
from app.gate.capability import Capability, CapabilityGrant, issue_grant, allows  # noqa: F401
from app.models import GatedResult, GateDecision  # noqa: F401

__all__ = [
    "evaluate",
    "GateError",
    "PartyNameResolver",
    "GatedResult",
    "GateDecision",
    "Capability",
    "CapabilityGrant",
    "issue_grant",
    "allows",
]
