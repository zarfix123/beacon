"""Capability-scoped requests — the second independent gate (permission-gate.md §2.3).

Responsibility: unforgeable in-process capability tokens that declare which tiers an
asker is entitled to RECEIVE. The gate checks the capability before deciding, so the
asker can never receive a tier it wasn't granted, independent of visibility. Two
independent gates (visibility policy AND capability) must both say "yes" for content
to cross.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Flag, auto

from app.models import GateDecision


class Capability(Flag):
    """What an asker is entitled to receive across the boundary."""
    NONE = 0
    PUBLIC_READ = auto()          # may receive full public payloads
    RESTRICTED_REQUEST = auto()   # may receive a redacted gist + request access
    PRIVATE_READ = auto()         # may receive private payloads (NEVER granted in MVP demo)


@dataclass(frozen=True)
class CapabilityGrant:
    """An unforgeable (in-process, frozen) capability the asker presents.

    Issued by the responding agent's policy for a given asker, NOT chosen by the
    asker. The asker cannot widen its own scope.
    """
    holder_agent_id: str          # who the grant is for (from_agent)
    capabilities: Capability      # bitmask of allowed tiers


# What each decision requires the asker to hold. DENIED requires nothing (no payload).
_REQUIRED: dict[GateDecision, Capability] = {
    GateDecision.FULL: Capability.PUBLIC_READ,
    GateDecision.REDACTED: Capability.RESTRICTED_REQUEST,
}


def issue_grant(for_agent_id: str) -> CapabilityGrant:
    """MVP issuer: every external asker gets PUBLIC_READ | RESTRICTED_REQUEST,
    never PRIVATE_READ. The SHAPE is real so the demo is not theatre."""
    return CapabilityGrant(
        holder_agent_id=for_agent_id,
        capabilities=Capability.PUBLIC_READ | Capability.RESTRICTED_REQUEST,
    )


def allows(grant: CapabilityGrant, decision: GateDecision) -> bool:
    """Does this grant permit the asker to RECEIVE the given decision's output?

    full -> needs PUBLIC_READ; redacted -> needs RESTRICTED_REQUEST; denied ->
    always allowed (carries no payload). The gate down-ranks to DENIED otherwise.
    """
    if decision is GateDecision.DENIED:
        return True
    return bool(grant.capabilities & _REQUIRED[decision])
