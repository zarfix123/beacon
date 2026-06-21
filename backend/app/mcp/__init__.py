"""MCP federation layer (Phase 5).

Beacon-as-MCP-client: connect to a party that serves its gated knowledge over a real MCP
server, and dispatch the fan-out so configured parties go over MCP while the rest stay
local. Feature-flagged with a local fallback (see app/mcp/client.py) — the MCP path can
never break the demo. The party server itself lives in scripts/mcp_party.py.
"""
