#!/usr/bin/env bash
# One-command demo launcher: backend (uvicorn :8000) + frontend (vite :5173).
#
# Exports the demo retrieval env BEFORE Python starts — search.py / responder.py read
# RELAY_SEARCH / RELAY_TOP_K at import time, so they MUST be set in the environment here
# (a .env loaded later by the app is too late for those import-time constants).
#
#   cd backend && ./scripts/run.sh        # Ctrl-C stops both
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$(dirname "$SCRIPT_DIR")"
ROOT="$(dirname "$BACKEND")"
FRONTEND="$ROOT/frontend"

export RELAY_SEARCH="${RELAY_SEARCH:-hybrid}"   # real engine: BM25 + dense + RRF
export RELAY_TOP_K="${RELAY_TOP_K:-2}"          # only the planted on-topic chunks per party
export RELAY_MIN_SIM="${RELAY_MIN_SIM:-0.35}"   # relevance floor: off-topic -> no-hit; one-party -> single-hit

pids=()
cleanup() { echo; echo "[run] shutting down…"; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "[run] backend  -> http://localhost:8000  (RELAY_SEARCH=$RELAY_SEARCH top_k=$RELAY_TOP_K)"
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

echo "[run] both up. Open http://localhost:5173 — Ctrl-C stops both."
wait
