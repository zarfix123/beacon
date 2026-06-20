"""Events subsystem: in-process async pub/sub keyed by query_id.

See backend/docs/router.md §2.4. The EventBus is the decoupled emit path the
orchestrator/router emit into; api/events.py WSManager subscribes per query_id and
forwards frames to live sockets (BUILD_INDEX.md §2.1 layered transport).
"""
