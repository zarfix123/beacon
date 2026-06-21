# Beacon — MCP integrations

How to query the Beacon permissioned knowledge network from Claude tools. Beacon speaks MCP in
**two directions**, and this folder captures the setup that otherwise lives outside the repo (in
`~/.config/Claude/` and `~/.claude/commands/`) so it's reproducible.

> ⚠️ The configs below hardcode an absolute path (`/home/dennis/Projects/beacon/backend`) and a
> Python interpreter (`/usr/bin/python3.10`). **Change both to match your checkout / environment.**

## The pieces (all in-repo)

| File | What it is |
|---|---|
| `backend/scripts/mcp_beacon_server.py` | **Outbound** MCP server — exposes Beacon *itself* as one `query(question)` tool. Query the whole network from any MCP client. Query-only (no grant). |
| `backend/scripts/mcp_party.py` | **Inbound** federation — serves one party (Helios) over a real MCP server, so Beacon's orchestrator federates it as an MCP client. Feature-flagged, local fallback. |
| `backend/app/mcp/client.py` | The MCP client + dispatcher the backend uses to federate a party (with timeout + local fallback). |
| `backend/scripts/beacon_ask.py` | Tiny terminal client for the outbound server (used by the Claude Code `/beacon` command). |

## Running everything

```bash
cd backend && ./scripts/run.sh
```
Starts four processes (Ctrl-C stops all):

| service | port | role |
|---|---|---|
| frontend (UI) | 5173 | the visual demo + hero beat |
| backend | 8000 | main app (Helios federated over MCP, others local) |
| Helios party MCP server | 9100 | inbound federation |
| Beacon outbound MCP server | 9200/mcp | outbound: `query` the network (streamable-HTTP) |

Escape hatches: `BEACON_MCP=off` (all parties local), `BEACON_OUTBOUND=off` (skip the outbound server).

---

## Claude Desktop

Claude Desktop spawns MCP servers itself over **stdio**. The entry lives in
`~/.config/Claude/claude_desktop_config.json` — a clean, beacon-only copy is in
[`claude-desktop/claude_desktop_config.json`](claude-desktop/claude_desktop_config.json). **Merge
the `beacon` entry into your existing `mcpServers`** (don't clobber other servers).

```json
{
  "mcpServers": {
    "beacon": {
      "command": "bash",
      "args": [
        "-c",
        "cd /home/dennis/Projects/beacon/backend && exec /usr/bin/python3.10 -m scripts.mcp_beacon_server"
      ]
    }
  }
}
```

**Why the `bash -c "cd … && exec python -m …"` wrapper?** Claude Desktop does **not** honor the
config's `cwd` field on Linux, so a plain `python -m scripts.mcp_beacon_server` dies with
`No module named 'scripts'`. Forcing the directory in the command itself fixes it. (Verified: the
server loads its corpora relative to the backend dir, so the `cd` is required.)

**After editing the config, fully quit and reopen Claude Desktop** — it only loads MCP servers at
launch (closing the window isn't enough).

**How to use it:** Beacon is opt-in. Either pick the **`/beacon` slash command** (exposed as an MCP
*prompt*), or start a message with the **`/beacon` flag**, e.g. `/beacon <question>`. The tool is
gated so it won't fire on ordinary messages.

---

## Claude Code

A custom slash command gives you `/beacon <question>` straight from the Claude Code prompt. Copy
[`claude-code/beacon.md`](claude-code/beacon.md) to `~/.claude/commands/beacon.md` (user-level, all
projects) — and update the absolute path inside it to your checkout.

It runs `beacon_ask.py` against the outbound server (`:9200`) and renders the result in two parts:
the **cold Beacon output verbatim** (synthesized answer + Sources + Per-party gating), then a short
**"My read:"** with the model's take. Requires the stack to be running (`./scripts/run.sh`).

---

## The gating (the whole point)

Every result carries the **Sources** + **Per-party results** showing each party's decision:
`full ✓` / `redacted 🔒 (request access)` / `denied ⛔`, with provenance. The outbound server
prepends a presentation directive and reinforces it in the tool description so consuming assistants
keep the gating visible instead of paraphrasing it away. This is **instruction-level**, not a hard
lock (MCP has no "render verbatim" enforcement) — the web UI is the guaranteed-visible surface.

**Best test prompt** (surfaces all three states):
> We're seeing 429s on checkout — who changed the rate limit on the payments path, and what is it now?

Northwind → full ✓ + denied ⛔ · Helios → full ✓ · Quanta → redacted 🔒 + full ✓.

## Notes

- **Query-only by design.** The outbound server exposes no grant/`set_visibility` tool — granting
  access stays in the Beacon UI, local and bulletproof. The grant never crosses MCP.
- **Separate processes.** The outbound server is independent of the main app; running it (or not)
  has zero effect on the visual demo.
- The outbound server reuses the orchestrator + synthesis verbatim — it rebuilds no pipeline.
