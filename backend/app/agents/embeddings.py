"""Embedding function + model id + dimension (agents-corpus-index.md §2.2).

Responsibility: one embedding function pair used to embed both corpus (offline /
startup) and queries (real cosine search). NOT a Claude model — Anthropic has no
embeddings endpoint. Default provider: local sentence-transformers all-MiniLM-L6-v2
(no API key, deterministic, EMBED_DIM=384). EMBED_MODEL/EMBED_DIM are pinned in ONE
place and synced with Hao at H8 (OQ-7). This is a SKELETON — no logic.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # local, no key (OQ-7)
EMBED_DIM = 384                                          # uniform across all agents


def embed_texts(texts: list[str]) -> "np.ndarray":
    """Return an (n, EMBED_DIM) float32 matrix. Used for corpus + query embedding."""
    raise NotImplementedError("embed_texts is a skeleton stub")


def embed_query(query: str) -> "np.ndarray":
    """Convenience: embed_texts([query])[0] -> shape (EMBED_DIM,)."""
    raise NotImplementedError("embed_query is a skeleton stub")
