"""Tests for app/gate/policy.py + capability (BUILD_INDEX.md §2 / steps 9-10).

TODO: assert the 3 tiers map correctly (public->full, restricted->redacted,
private->denied), fail-closed on an unknown tier, and that a public-layer capability
grant down-ranks private->denied (full needs PUBLIC_READ, redacted needs RESTRICTED_REQUEST).

Placeholder — no real assertions yet.
"""
