"""Tests for app/events/bus.py — pub/sub, history replay, drop-never-block."""
from __future__ import annotations

from app.events.bus import EventBus


async def test_two_subscribers_both_receive():
    bus = EventBus()
    q1 = bus.subscribe("q1")
    q2 = bus.subscribe("q1")
    await bus.emit("q1", {"type": "x"})
    assert (await q1.get())["type"] == "x"
    assert (await q2.get())["type"] == "x"


async def test_emit_to_no_subscribers_is_noop():
    bus = EventBus()
    await bus.emit("nobody", {"type": "x"})   # must not raise


async def test_late_subscriber_gets_replayed_history():
    bus = EventBus()
    await bus.emit("q1", {"n": 1})
    await bus.emit("q1", {"n": 2})
    q = bus.subscribe("q1")                    # subscribed AFTER the emits
    assert (await q.get())["n"] == 1
    assert (await q.get())["n"] == 2


async def test_unsubscribe_stops_delivery():
    bus = EventBus()
    q = bus.subscribe("q1")
    bus.unsubscribe("q1", q)
    await bus.emit("q1", {"n": 1})
    assert q.empty()


async def test_full_queue_drops_without_raising():
    bus = EventBus()
    q = bus.subscribe("q1")
    for _ in range(q.maxsize):                 # fill it to the brim
        q.put_nowait({})
    await bus.emit("q1", {"dropped": True})     # drop-never-block: must not raise
    assert q.full()
