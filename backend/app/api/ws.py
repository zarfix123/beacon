"""/ws/query WebSocket endpoint (api-websocket.md §2.8).

Responsibility: support BOTH transport options on one endpoint — WS-driven
(type:query -> ack, then stream events on this socket) and POST+WS (type:subscribe to
an existing query_id). Cleans up the socket on disconnect. This is a SKELETON — no
logic.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.orchestrator.orchestrator import new_query_id
from app.run_registry import RunContext

router = APIRouter()


@router.websocket("/ws/query")
async def ws_query(ws: WebSocket) -> None:
    """Accept the socket, then loop on frames (both transport options on one endpoint):

    - `{type:"query"}`  -> mint a run, send `ack`, subscribe this socket BEFORE starting
      the run (so no frame is missed), then kick the orchestrator. Events stream via the
      WSManager pump; this handler stays in its receive loop to keep the socket alive (so a
      later grant-access replay re-streams here) and to detect disconnect.
    - `{type:"subscribe", query_id}` -> bind this socket to an existing run (POST+WS path);
      the bus replays any frames already emitted.
    Unknown frames are ignored. Unsubscribe on disconnect.
    """
    await ws.accept()
    state = ws.app.state
    try:
        while True:
            frame = await ws.receive_json()
            ftype = frame.get("type") if isinstance(frame, dict) else None

            if ftype == "query":
                asker = frame.get("from_agent") or state.settings.default_asker
                query = frame.get("query") or ""
                query_id = new_query_id()
                agents = [aid for aid in state.registry.all_ids() if aid != asker]
                state.run_registry.put(RunContext(query_id=query_id, query=query, from_agent=asker))
                # ack first (no concurrent send), then subscribe, then start the run.
                await ws.send_json({"type": "ack", "query_id": query_id,
                                    "from_agent": asker, "agents": agents})
                await ws.app.state.ws_manager.subscribe(query_id, ws)
                state.orchestrator.start_run(query_id, asker, query)

            elif ftype == "subscribe":
                query_id = frame.get("query_id")
                if query_id:
                    await state.ws_manager.subscribe(query_id, ws)
            # unknown frame types are ignored
    except WebSocketDisconnect:
        pass
    finally:
        await state.ws_manager.unsubscribe_socket(ws)
