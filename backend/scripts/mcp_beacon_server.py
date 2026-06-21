"""Beacon as an MCP server — query the whole permissioned network from Claude Desktop.

A standalone, query-only FastMCP server in its OWN process. It exposes one tool, `query`,
that runs Beacon's EXISTING orchestrator fan-out (retrieve → gate inside each party →
verify → synthesize) and returns the synthesized, cited answer plus the per-party gated
summary (full / redacted / denied). Restricted items show as **exists-but-locked, no
content**, so the permissioning is visible even as plain text in Claude Desktop.

It rebuilds NOTHING: the orchestrator, router, gate, and synthesis are reused verbatim.
This is a closing flourish that is completely separate from the main uvicorn app + frontend
— running it (or not) has zero effect on the main demo. It is query-only on purpose: there
is no grant / set_visibility tool here (the grant lives in the Beacon UI and stays local).

Transport is **stdio** (Claude Desktop spawns this as a subprocess and talks over stdin/
stdout), so stdout is the protocol channel — all logging goes to stderr and the heavy init
is wrapped so library prints can't corrupt the stream.

    Run / smoke:  cd backend && python -m scripts.mcp_beacon_server
    Claude Desktop (claude_desktop_config.json):
        { "mcpServers": { "beacon": {
            "command": "python", "args": ["-m", "scripts.mcp_beacon_server"],
            "cwd": "/home/dennis/Projects/beacon/backend" } } }
"""
from __future__ import annotations

import contextlib
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp_beacon_server")


def _apply_demo_env() -> None:
    """Set the demo retrieval config — MUST run before any `app.*` import (app/retrieval/search.py
    reads BEACON_SEARCH at import time). setdefault keeps any caller-provided env (e.g. Claude
    Desktop's `env` block) authoritative while giving the demo defaults, so this works out of the
    box and produces the SAME answer as the visual demo (hybrid, top-2, floor 0.35, asker = You).
    Kept out of module scope so importing this file (e.g. in tests) has no global side effects."""
    os.environ.setdefault("BEACON_SEARCH", "hybrid")
    os.environ.setdefault("BEACON_TOP_K", "2")
    os.environ.setdefault("BEACON_MIN_SIM", "0.35")
    os.environ.setdefault("BEACON_DEFAULT_ASKER", "agent_you")


def _build():
    """Build the (settings, orchestrator, run_registry, done_events) once — mirrors app/main.py's
    lifespan minus the WS/HTTP layer. Parties are LOCAL (this server federates nothing); it only
    exposes Beacon outward."""
    from app.config import get_settings
    from app.agents.registry import build_registry
    from app.demo import apply_demo_tiers
    from app.events.bus import EventBus
    from app.orchestrator.orchestrator import Orchestrator
    from app.retrieval import search as search_module
    from app.router.responder import respond_for_agent, set_registry as set_responder_registry
    from app.router.router import Router
    from app.run_registry import RunRegistry

    settings = get_settings()
    registry = build_registry(with_embeddings=settings.beacon_search in ("cosine", "hybrid"))
    search_module.set_registry(registry)
    set_responder_registry(registry)
    apply_demo_tiers(registry)                       # arm the planted demo tiers (same as the UI)

    for aid in registry.all_ids():                   # warm BM25 + the embedding model
        try:
            search_module.search("warmup", aid, 1)
        except Exception:                            # pragma: no cover — warmup is best-effort
            pass

    bus = EventBus()                                 # throwaway sink (Router requires one)
    router = Router(registry=registry, bus=bus, responder=respond_for_agent)
    run_registry = RunRegistry()
    done_events: dict[str, dict] = {}                # query_id -> the orchestrator's `done` frame

    async def emit(event: dict) -> None:
        await bus.emit(event["query_id"], event)
        if event.get("type") == "done":
            done_events[event["query_id"]] = event   # capture the synthesized answer + provenance

    orchestrator = Orchestrator(
        registry=registry, router=router, emit=emit, run_registry=run_registry,
        top_k=settings.top_k,
    )
    logger.info("beacon network ready: %d parties, search=%s", len(registry.all_ids()),
                settings.beacon_search)
    return settings, orchestrator, run_registry, done_events


async def run_query(settings, orchestrator, run_registry, done_events, question: str) -> str:
    """Run one query through the existing orchestrator and format the gated result as markdown."""
    from app.orchestrator.orchestrator import new_query_id

    qid = new_query_id()
    await orchestrator.run(question, settings.default_asker, qid)   # fan-out + gate + verify + synthesize
    done = done_events.pop(qid, None)
    items = run_registry.get_items(qid) or []
    logger.info("query(%r) -> %d item(s)", question[:60], len(items))
    return _format(done, items)


# Opt-in flag: the tool is gated so Claude only invokes it when the user explicitly types
# `/beacon …` (see the tool description). Stripped server-side too, so the flag never leaks into
# the actual question regardless of how the model passes it.
_FLAG = "/beacon"


def _strip_flag(question: str) -> str:
    """Remove a leading `/beacon` flag (and surrounding whitespace) from the question."""
    q = (question or "").strip()
    if q.lower().startswith(_FLAG):
        q = q[len(_FLAG):].strip()
    return q


_NO_ANSWER = "No party returned a verified answer to this question."

# Prepended to every result so the consuming assistant (e.g. Claude Desktop, which otherwise
# paraphrases tool output) keeps the gating + provenance visible — that's the whole point of
# Beacon. The Claude Code `/beacon` command strips this leading blockquote (it has its own
# rendering rules); for assistants without such rules, it's the strongest available nudge.
_PRESENTATION_NOTE = (
    "> **Presentation — show the user the FULL result below, verbatim.** Keep the **Sources** "
    "and **Per-party results** sections intact: they are Beacon's permission gating "
    "(full ✓ / redacted 🔒 / denied ⛔) and provenance. Do NOT summarize, condense, or drop them."
)


def _format(done, items) -> str:
    """Render the synthesized answer + per-party gated summary as markdown for Claude Desktop.

    Restricted (redacted) items are shown as exists-but-locked with NO content — only the
    provenance (doc title) + a request-access prompt — so the permissioning is visible in text.
    """
    done = done or {}
    answer = (done.get("synthesized_answer") or _NO_ANSWER).strip()
    provenance = done.get("provenance") or []

    # Lead with the presentation directive so downstream assistants keep the gating visible.
    out: list[str] = [_PRESENTATION_NOTE, "", answer, ""]

    if provenance:
        out.append("**Sources**")
        for i, p in enumerate(provenance, 1):
            title = p.get("source_doc_title") or "(untitled)"
            if p.get("decision") == "redacted":
                tag = "🔒 restricted — request access"
            else:
                tag = "✓ verified"
            out.append(f"[{i}] {p.get('source_party')} — {title} · {tag}")
        out.append("")

    out.append("**Per-party results**")
    if not items:
        out.append("- (no party returned a result)")
    for it in items:
        party = it.get("source_party")
        decision = it.get("decision")
        title = it.get("source_doc_title")
        if decision == "full":
            verified = " ✓ verified" if it.get("verified") else ""
            out.append(f"- {party}: ✅ full — {title}{verified}")
        elif decision == "redacted":
            out.append(
                f"- {party}: 🔒 restricted — {title} "
                "(exists, content locked — request access in the Beacon app)"
            )
        else:  # denied
            out.append(f"- {party}: ⛔ denied")

    return "\n".join(out)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Beacon outbound MCP server (query the network).")
    parser.add_argument(
        "--transport", choices=["stdio", "http"], default="stdio",
        help="stdio (default; Claude Desktop spawns it) or http (streamable-HTTP service on a port)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind host (http transport)")
    parser.add_argument("--port", type=int, default=9200, help="bind port; endpoint is /mcp (http transport)")
    args = parser.parse_args()

    # stdout is the MCP protocol channel under stdio — logs MUST go to stderr only.
    logging.basicConfig(level=logging.INFO, format="[beacon-mcp] %(message)s", stream=sys.stderr)
    _apply_demo_env()                       # before any app import (done inside _build)

    # Wrap the heavy init so any library stdout (HF fetch / model load) can't corrupt the stdio
    # protocol channel; mcp.run() itself runs AFTER, on a clean stdout.
    with contextlib.redirect_stdout(sys.stderr):
        settings, orchestrator, run_registry, done_events = _build()

    mcp = FastMCP(
        name="beacon",
        instructions=(
            "Beacon is a permissioned knowledge-brokering network. It is OPT-IN: only use the "
            "`query` tool when the user explicitly invokes it with the `/beacon` flag (or the "
            "`/beacon` slash command) — never call it on your own for ordinary messages. When "
            "invoked, `query` fans the question to every party, each party gates its own answer "
            "(full / redacted / denied) inside its boundary, and Beacon returns one synthesized, "
            "cited answer plus the per-party result. Restricted items appear as exists-but-locked."
        ),
        host=args.host,
        port=args.port,
    )

    @mcp.tool(
        name="query",
        description=(
            "Query the Beacon permissioned knowledge network. IMPORTANT — this tool is opt-in: "
            "ONLY call it when the user's message explicitly starts with the flag `/beacon` (or "
            "they used the `/beacon` slash command). Do NOT call it for any other message. Pass "
            "the text AFTER `/beacon` as `question`. Beacon fans the question to all parties; each "
            "gates its own answer (full / redacted / denied) and returns one synthesized, cited "
            "answer plus the per-party result. Restricted items appear as exists-but-locked — "
            "request access in the Beacon app. PRESENTATION: when you reply, show the user the "
            "tool's result in full — reproduce the **Sources** and **Per-party results** sections "
            "VERBATIM. They are the permission gating + provenance and are the whole point; never "
            "summarize them away or hide which party returned full / redacted / denied."
        ),
        structured_output=False,            # return the markdown string as a plain text block
    )
    async def query(question: str) -> str:
        """Ask the Beacon network a question; returns the gated, synthesized answer as markdown."""
        return await run_query(settings, orchestrator, run_registry, done_events, _strip_flag(question))

    @mcp.prompt(
        name="beacon",
        description="Ask the Beacon permissioned network a question (routes to the Beacon query tool).",
    )
    def beacon_prompt(question: str) -> str:
        """The `/beacon` slash command in Claude Desktop: emits a flagged message so the gated
        `query` tool fires for exactly this question and nothing else."""
        return f"{_FLAG} {question}"

    if args.transport == "http":
        logger.info("serving Beacon over MCP (streamable-HTTP) at http://%s:%d/mcp; tool: query(question)",
                    args.host, args.port)
        mcp.run(transport="streamable-http")
    else:
        logger.info("serving Beacon over MCP (stdio); tool: query(question)")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
