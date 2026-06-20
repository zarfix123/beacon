"""Retrieval subsystem: the frozen search() entry point.

See backend/docs/agents-corpus-index.md §2.6 and shared/contracts/search-interface.md.
Holds the keyword stub (until H8) and the real cosine path behind one selectable
backend. Gate-free: returns all visibility tiers, ungated.
"""
