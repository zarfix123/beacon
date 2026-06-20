"""Shared test fixtures (BUILD_INDEX.md §2 tests/conftest.py).

TODO: provide fixtures used across the suite:
  - a fake EventBus / WSManager sink that records emitted frames in order;
  - a fake responder returning canned ResponseItems (one full, one redacted, one denied);
  - seeded chunk dicts (data-model §2 shape) including the restricted servo chunk and a
    private chunk, for gate / leakage / redaction tests.

This is a SKELETON — no fixtures implemented yet.
"""
