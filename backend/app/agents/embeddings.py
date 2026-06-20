"""Embedding function + model id + dimension (agents-corpus-index.md §2.2).

Responsibility: one embedding-function pair used to embed both the corpus (offline /
startup) and queries (the dense channel of retrieval). NOT a Claude model — Anthropic
has no embeddings endpoint.

Provider: model2vec STATIC embeddings (`minishlab/potion-retrieval-32M`) — the best
static retrieval model available, ~82% of all-MiniLM-L6-v2 retrieval quality at ~32MB
with **numpy-only inference (no torch)**, so cold start is instant and the install is
trivial. EMBED_MODEL/EMBED_DIM are pinned in ONE place (OQ-7). `model2vec` is imported
lazily so the keyword-stub path never loads it.
"""
from __future__ import annotations

import numpy as np

EMBED_MODEL = "minishlab/potion-retrieval-32M"   # static, numpy-only, no key (OQ-7)
EMBED_DIM = 512                                   # potion-retrieval-32M output dim

_MODEL = None   # lazily-loaded model2vec StaticModel singleton


def _get_model():
    global _MODEL
    if _MODEL is None:
        from model2vec import StaticModel  # lazy: only the dense path pulls this in
        _MODEL = StaticModel.from_pretrained(EMBED_MODEL)
    return _MODEL


def embed_texts(texts: list[str]) -> "np.ndarray":
    """Return an (n, EMBED_DIM) float32 matrix. Used for corpus + query embedding.

    Vectors are L2-normalized so a dot product equals cosine similarity.
    """
    model = _get_model()
    vecs = np.asarray(model.encode(texts), dtype="float32")
    if vecs.ndim == 1:
        vecs = vecs.reshape(1, -1)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return (vecs / np.clip(norms, 1e-9, None)).astype("float32")


def embed_query(query: str) -> "np.ndarray":
    """Convenience: embed_texts([query])[0] -> shape (EMBED_DIM,)."""
    return embed_texts([query])[0]
