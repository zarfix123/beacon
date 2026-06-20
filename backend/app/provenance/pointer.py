"""Provenance pointer assembly — no Claude (provenance-verification.md §2.2).

Build the ProvenancePointer from a gated chunk. Pure, deterministic, no network.
NEVER reads chunk["text"] or chunk["embedding"]. `payload_hidden=True` suppresses the
doc title for denied existence-only items.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from app.models import ProvenancePointer


def assemble_provenance(
    chunk: dict,
    *,
    payload_hidden: bool = False,
    resolve_party_name: Optional[Callable[[str], str]] = None,
) -> ProvenancePointer:
    """Build the provenance pointer from a gated chunk (data-model §2 dict).

    Reads ONLY `owner`, `doc_title`, `chunk_id` — never `text`/`embedding`. Resolves
    owner -> party_name via the injected resolver (falls back to the raw owner id).
    `payload_hidden=True` suppresses the doc title (denied/private). `timestamp` is
    internal (logs only) and is never serialized to the wire.
    """
    owner = chunk["owner"]
    party = resolve_party_name(owner) if resolve_party_name is not None else owner
    return ProvenancePointer(
        source_party=party,
        source_doc_title=(None if payload_hidden else chunk["doc_title"]),
        owner=owner,
        chunk_id=chunk["chunk_id"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
