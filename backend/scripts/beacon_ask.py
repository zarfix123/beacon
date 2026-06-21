"""Tiny terminal client for the Beacon outbound MCP server — try it without Claude Desktop.

Connects to the running outbound server (streamable-HTTP, default http://localhost:9200/mcp,
started by run.sh) over the real MCP protocol and calls its `query` tool. Pass a question, or
omit it for an interactive REPL.

    cd backend
    python -m scripts.beacon_ask "who changed the rate limit on the payments path?"
    python -m scripts.beacon_ask            # interactive: type questions, Ctrl-D to quit
"""
from __future__ import annotations

import asyncio
import os
import sys


URL = os.getenv("BEACON_MCP_OUTBOUND_URL", "http://localhost:9200/mcp")


def _text(result) -> str:
    for block in (getattr(result, "content", None) or []):
        if getattr(block, "text", None):
            return block.text
    return "(no content returned)"


async def _ask(session, question: str) -> None:
    result = await session.call_tool("query", {"question": question})
    print("\n" + _text(result) + "\n")


async def main() -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    question = " ".join(sys.argv[1:]).strip()
    try:
        async with streamablehttp_client(URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if question:
                    await _ask(session, question)
                    return
                print(f"Connected to Beacon at {URL}. Ask the network a question (Ctrl-D to quit).")
                loop = asyncio.get_event_loop()
                while True:
                    try:
                        q = (await loop.run_in_executor(None, lambda: input("\nbeacon> "))).strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return
                    if q:
                        await _ask(session, q)
    except Exception as exc:                     # connection refused etc.
        print(f"Could not reach the Beacon outbound server at {URL}: {exc}", file=sys.stderr)
        print("Is it running? Start the stack with `cd backend && ./scripts/run.sh`.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
