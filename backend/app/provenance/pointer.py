"""Provenance pointer assembly — no Claude (provenance-verification.md §2.2).

Responsibility: build the ProvenancePointer from a gated chunk + the agent registry.
Pure, deterministic, no network. NEVER reads chunk["text"] or chunk["embedding"].
`payload_hidden=True` suppresses the doc title for denied existence-only items.
This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import ProvenancePointer


def assemble_provenance(chunk: dict, *, payload_hidden: bool = False) -> ProvenancePointer:
    """Build the provenance pointer from a gated chunk (data-model §2 dict).

    Resolves owner -> party_name via the registry. `payload_hidden=True` for denied
    items where even the doc title may be suppressed (spec §3 private tier). Never
    reads chunk['text'] or chunk['embedding']. `timestamp` is internal (logs only).
    """
    raise NotImplementedError("assemble_provenance is a skeleton stub")
