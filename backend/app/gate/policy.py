"""Pure visibility->decision policy (permission-gate.md §2.2).

Responsibility: the visibility->decision mapping (data-model.md §4 reference table)
as a PURE function — no Claude, no network, deterministic. The single source of truth
for the mapping. Fail-closed: an unrecognized tier raises rather than defaulting to
full.
"""
from __future__ import annotations

from app.models import GateDecision, Visibility

# The frozen mapping (data-model.md §4). Defined ONCE here.
_VISIBILITY_TO_DECISION: dict[str, GateDecision] = {
    "public": GateDecision.FULL,
    "restricted": GateDecision.REDACTED,
    "private": GateDecision.DENIED,
}

# Whether a denied (private) item shows an existence-only pointer (spec §3 / OQ-2).
# MVP: hidden (show nothing). Single knob, here.
SHOW_EXISTENCE_FOR_PRIVATE: bool = False


def decide(visibility: Visibility) -> GateDecision:
    """Map a chunk's visibility tier to a gate decision. Pure, total over the enum.

    Raises GateError on an unknown visibility value (fail-closed: an unrecognized
    tier is a hard error, never silently allowed through).
    """
    try:
        return _VISIBILITY_TO_DECISION[visibility]
    except KeyError as exc:
        # Lazy import dodges the gate.gate <-> policy import cycle.
        from app.gate.gate import GateError

        raise GateError(f"unknown visibility tier: {visibility!r}") from exc
