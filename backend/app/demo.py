"""Locked demo scenario: planted rate-limit/429s chunks + tiers + query (Phase 4 step 1).

The 3 real corpora are domain-disjoint (coding vs admissions essays vs security audits), so
no organic query yields a coherent cross-party answer. This coherent scenario is PLANTED to
make the grant-access money moment reliable — synthetic data, sanctioned for the demo.

Single source of truth shared by:
  - scripts/demo_seed.py        -> writes these chunks to the corpora on disk + embeds them
  - POST /demo/reset (api)       -> re-applies the tiers to the LIVE in-memory index between
                                    rehearsal takes (grant-access flips one to public live;
                                    this re-arms it without a server restart)

Topology: asker = agent_helios (excluded from fan-out). Responders = northwind + quanta:
  northwind -> {public full, private denied},  quanta -> {public full, restricted redacted}.
Every text overlaps the demo query's distinctive tokens (429, rate limit, payments, checkout,
throttle, req/min) so the planted chunks rank top-2 under hybrid retrieval, out-ranking the
off-topic real chunks.
"""
from __future__ import annotations

DEMO_QUERY = (
    "We're seeing 429s on checkout — who changed the rate limit on the payments path, "
    "and what is it now?"
)

DEMO_CHUNKS: list[dict] = [
    {
        "chunk_id": "northwind_demo_gateway",
        "parent_doc_id": "northwind_demo",
        "doc_title": "billing-svc/RetryPolicy.md",
        "owner": "agent_northwind",
        "visibility": "public",
        "text": (
            "The payments gateway rate limit on the checkout path is currently 60 requests per "
            "minute. The platform team lowered it from 120 to 60 requests/minute during the "
            "retry-queue refactor, to relieve the downstream retry storm. It is a deliberate, "
            "temporary change that automatically reverts to 120 requests/minute at 16:00 UTC. The "
            "429 errors customers are seeing on checkout are the expected effect of this lower "
            "limit."
        ),
    },
    {
        "chunk_id": "northwind_demo_runbook",
        "parent_doc_id": "northwind_demo",
        "doc_title": "payments/incident-runbook.md",
        "owner": "agent_northwind",
        "visibility": "private",
        "text": (
            "Payments checkout incident runbook for the rate-limit / 429 scenario: on-call "
            "escalation paths, the emergency rate-limit override procedure for the checkout "
            "gateway, and the customer-impact comms templates. Owned by the Data/SRE team; "
            "internal use only, not for cross-team sharing."
        ),
    },
    {
        "chunk_id": "quanta_demo_throttle",
        "parent_doc_id": "quanta_demo",
        "doc_title": "auth-core/throttle.yaml",
        "owner": "agent_quanta",
        "visibility": "restricted",
        "text": (
            "auth-core throttles the payments checkout path by capping token issuance at 30 "
            "requests/minute per service. This is the second rate limit on the payments path, in "
            "addition to the billing gateway limit. Raising the cap requires a security review and "
            "sign-off from the security team."
        ),
    },
    {
        "chunk_id": "quanta_demo_notes",
        "parent_doc_id": "quanta_demo",
        "doc_title": "auth-core/README.md",
        "owner": "agent_quanta",
        "visibility": "public",
        "text": (
            "auth-core applies a per-service token-issuance throttle on the payments checkout path, "
            "in addition to the billing gateway's rate limit. The exact threshold is managed by the "
            "security team in throttle.yaml; contact them for the current value or to request a "
            "temporary increase to relieve checkout 429s."
        ),
    },
]

# Non-public tiers to (re)apply. Public chunks need no entry (public is the default).
DEMO_TIERS: dict[str, str] = {
    c["chunk_id"]: c["visibility"] for c in DEMO_CHUNKS if c["visibility"] != "public"
}


def apply_demo_tiers(registry) -> dict[str, str]:
    """Re-apply the locked demo tiers to a LIVE registry's in-memory chunks (POST /demo/reset).

    Resets the granted chunk back to restricted between rehearsal takes without a restart.
    Returns the applied {chunk_id: visibility}; silently skips ids not present (no-op safe).
    """
    applied: dict[str, str] = {}
    for chunk_id, visibility in DEMO_TIERS.items():
        try:
            agent, _ = registry.find_chunk(chunk_id)
        except KeyError:
            continue
        agent.index.set_visibility(chunk_id, visibility)
        applied[chunk_id] = visibility
    return applied
