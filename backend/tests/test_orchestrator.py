"""Tests for app/orchestrator/orchestrator.py (BUILD_INDEX.md §2 / step 20).

TODO: assert event order against a fake sink — all agent-activated first, then N
response-item, then exactly one done; item_count == number of response-item events;
a verify->False still emits the item.

Placeholder — no real assertions yet.
"""
