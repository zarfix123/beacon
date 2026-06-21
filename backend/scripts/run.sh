#!/usr/bin/env bash
# One-command demo launcher: backend (uvicorn :8000) + frontend (vite :5173).
#
# Exports the demo retrieval env BEFORE Python starts — search.py / responder.py read
# BEACON_SEARCH / BEACON_TOP_K at import time, so they MUST be set in the environment here
# (a .env loaded later by the app is too late for those import-time constants).
#
#   cd backend && ./scripts/run.sh        # Ctrl-C stops both
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$(dirname "$SCRIPT_DIR")"
ROOT="$(dirname "$BACKEND")"
FRONTEND="$ROOT/frontend"

export BEACON_SEARCH="${BEACON_SEARCH:-hybrid}"   # real engine: BM25 + dense + RRF
export BEACON_TOP_K="${BEACON_TOP_K:-2}"          # only the planted on-topic chunks per party
export BEACON_MIN_SIM="${BEACON_MIN_SIM:-0.35}"   # relevance floor: off-topic -> no-hit; one-party -> single-hit

pids=()
cleanup() { echo; echo "[run] shutting down…"; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# ---- MCP federation (Phase 5): serve Helios over a real MCP server, then point the backend
# at it. The backend's dispatcher federates Helios over MCP and falls back to local if the
# server is down — so `BEACON_MCP=off ./scripts/run.sh` runs the whole demo all-local.
MCP_AGENT="${BEACON_MCP_AGENT:-agent_helios}"
MCP_PORT="${BEACON_MCP_PORT:-9100}"
if [ "${BEACON_MCP:-on}" != "off" ]; then
  echo "[run] mcp-party ($MCP_AGENT) -> http://localhost:$MCP_PORT/mcp"
  ( cd "$BACKEND" && exec python -m scripts.mcp_party --agent-id "$MCP_AGENT" --port "$MCP_PORT" ) &
  pids+=($!)
  echo -n "[run] waiting for mcp-party (loads embeddings)"
  for _ in $(seq 1 60); do
    if (exec 3<>"/dev/tcp/127.0.0.1/$MCP_PORT") 2>/dev/null; then exec 3>&- 3<&-; echo " — ok"; break; fi
    echo -n "."; sleep 0.5
  done
  export BEACON_MCP_AGENTS="$MCP_AGENT"
  export BEACON_MCP_URL="http://localhost:$MCP_PORT/mcp"
else
  echo "[run] BEACON_MCP=off — all parties local (no MCP server)"
fi

echo "[run] backend  -> http://localhost:8000  (BEACON_SEARCH=$BEACON_SEARCH top_k=$BEACON_TOP_K)"
( cd "$BACKEND" && exec uvicorn app.main:app --port 8000 ) &
pids+=($!)

echo -n "[run] waiting for backend health"
for _ in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then echo " — ok"; break; fi
  echo -n "."; sleep 0.5
done

echo "[run] frontend -> http://localhost:5173  (vite)"
( cd "$FRONTEND" && exec npm run dev ) &
pids+=($!)

# ---- Outbound MCP server: expose Beacon ITSELF over MCP (query the whole network from Claude
# Desktop / any MCP client). Standalone + query-only; separate from the main app. Claude Desktop
# uses the stdio entry in claude_desktop_config.json (it spawns its own); this http instance is
# the always-on service for terminal try-out / URL clients. `BEACON_OUTBOUND=off` skips it.
OUT_PORT="${BEACON_OUTBOUND_PORT:-9200}"
if [ "${BEACON_OUTBOUND:-on}" != "off" ]; then
  echo "[run] beacon-mcp -> http://localhost:$OUT_PORT/mcp  (outbound: query the network)"
  ( cd "$BACKEND" && exec python -m scripts.mcp_beacon_server --transport http --port "$OUT_PORT" ) &
  pids+=($!)
fi

echo "[run] up. Open http://localhost:5173 — Ctrl-C stops everything."
wait
