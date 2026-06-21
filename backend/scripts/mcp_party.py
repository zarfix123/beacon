"""Standalone party MCP server — one party's gated knowledge served over MCP (Phase 5, plan step 2).

Run as an independent process:

    cd backend && python -m scripts.mcp_party --agent-id agent_helios --port 9100

It builds a SINGLE-party registry (only this party's corpus — faithful to "a party holds
only its own data"), wires search + responder against it, and exposes ONE tool:

    respond(query: str) -> str   # JSON list[ResponseItem]

The retrieve → gate → redact → verify pipeline runs INSIDE this process (it reuses
`app.router.responder.respond_for_agent` verbatim — no new pipeline logic). Only already-gated
items cross the MCP boundary, so restricted text never leaves the party: the structural no-leak
invariant holds across the wire exactly as it does in-process. Served over streamable-HTTP at
http://<host>:<port>/mcp.
"""
from __future__ import annotations

import argparse
import json
import logging

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="[mcp-party] %(message)s")
logger = logging.getLogger("mcp_party")


def build_single_party_registry(agent_id: str):
    """Build a registry holding ONLY this party's index, and wire search + responder to it.

    Uses `with_embeddings=True` so the server runs the real hybrid retrieval its corpus was
    embedded for. Applies the locked demo tiers (a no-op for parties without a restricted demo
    chunk) and pre-warms BM25 + the embedding model so the first MCP call isn't a cold start.
    """
    from app.agents.agent import RuntimeAgent
    from app.agents.index import load_agent_index
    from app.agents.registry import AGENT_DEFS, AgentRegistry
    from app.demo import apply_demo_tiers
    from app.retrieval import search as search_module
    from app.router import responder as responder_module

    party_name = next((name for aid, name, _ in AGENT_DEFS if aid == agent_id), agent_id)
    index = load_agent_index(agent_id, with_embeddings=True)
    agent = RuntimeAgent(
        id=agent_id, party_name=party_name, scope_policy="three_tier", index=index
    )
    registry = AgentRegistry({agent_id: agent})

    search_module.set_registry(registry)        # search() resolves against this one party
    responder_module.set_registry(registry)     # respond_for_agent resolves party_name
    apply_demo_tiers(registry)                   # re-arm any planted tiers this party owns (no-op otherwise)

    try:                                         # warm BM25 + model2vec so the first call is snappy
        search_module.search("warmup", agent_id, 1)
    except Exception:                            # pragma: no cover — warmup is best-effort
        pass

    logger.info(
        "loaded party %s (%s): %d chunks, embeddings=%s",
        agent_id, party_name, len(index.chunks), index.matrix is not None,
    )
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Beacon party MCP server (one party served over MCP).")
    parser.add_argument("--agent-id", default="agent_helios", help="the single party this server serves")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=9100, help="bind port (endpoint is /mcp)")
    args = parser.parse_args()

    # Wire the single-party registry BEFORE importing respond_for_agent's call path runs.
    build_single_party_registry(args.agent_id)
    from app.router.responder import respond_for_agent

    mcp = FastMCP(
        name=f"beacon-party-{args.agent_id}",
        instructions=(
            "Beacon party knowledge server. The `respond` tool answers a query against THIS "
            "party's corpus and returns only gated items — the permission gate, redaction, and "
            "verification all run inside this server, so restricted content never crosses."
        ),
        host=args.host,
        port=args.port,
    )

    @mcp.tool(
        name="respond",
        description=(
            "Answer a query against this party's corpus. Returns a JSON array of gated response "
            "items (full / redacted / denied); the gate runs inside this server."
        ),
        structured_output=False,            # return the JSON string as a plain text block
    )
    async def respond(query: str) -> str:
        """Run the boundary pipeline for this party; return the gated items as a JSON string."""
        items = await respond_for_agent(args.agent_id, query)
        logger.info("respond(%r) -> %d gated item(s)", query[:60], len(items))
        return json.dumps(items)

    logger.info("serving %s over streamable-HTTP at http://%s:%d/mcp", args.agent_id, args.host, args.port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
