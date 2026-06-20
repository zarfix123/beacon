"""Embedding function + model id + dimension (agents-corpus-index.md §2.2).

Responsibility: one embedding function pair used to embed both corpus (offline /
startup) and queries (real cosine search). NOT a Claude model — Anthropic has no
embeddings endpoint. Default provider: local sentence-transformers all-MiniLM-L6-v2
(no API key, deterministic, EMBED_DIM=384). EMBED_MODEL/EMBED_DIM are pinned in ONE
place (OQ-7).

`sentence-transformers` / `torch` are imported lazily on first use so the keyword-stub
retrieval path (Phase 1) never pulls in torch.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # local, no key (OQ-7)
EMBED_DIM = 384                                          # uniform across all agents

_MODEL = None   # lazily-loaded SentenceTransformer singleton


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer  # lazy: torch only here
        _MODEL = SentenceTransformer(EMBED_MODEL)
    return _MODEL


def embed_texts(texts: list[str]) -> "np.ndarray":
    """Return an (n, EMBED_DIM) float32 matrix. Used for corpus + query embedding.

    Vectors are L2-normalized so a dot product equals cosine similarity.
    """
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")


def embed_query(query: str) -> "np.ndarray":
    """Convenience: embed_texts([query])[0] -> shape (EMBED_DIM,)."""
    return embed_texts([query])[0]
