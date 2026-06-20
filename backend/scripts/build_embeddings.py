"""One-shot offline: embed every corpus chunk -> data/embeddings.npz
(agents-corpus-index.md §2 / step 10, BUILD_INDEX.md §2).

Responsibility: read app/data/corpora/*.json, embed each chunk with EMBED_MODEL, and
write app/data/embeddings.npz keyed by chunk_id, so startup doesn't re-embed every
boot (index-once-before-demo, spec §9). Run once before the demo. This is a
SKELETON — no logic.
"""
from __future__ import annotations


def build_embeddings() -> None:
    """Read corpora, embed every chunk, write data/embeddings.npz keyed by chunk_id."""
    raise NotImplementedError("build_embeddings is a skeleton stub")


if __name__ == "__main__":
    build_embeddings()
