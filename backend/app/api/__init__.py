"""API subsystem: the HTTP/WebSocket edge of the backend.

See backend/docs/api-websocket.md. Owns the Pydantic wire models (schemas.py), the
WSManager bridging EventBus -> sockets (events.py), POST /query (http.py), and the
/ws/query endpoint (ws.py). No business logic — the transport + orchestration shell.
"""
