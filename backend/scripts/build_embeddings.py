"""One-shot offline: embed every corpus chunk -> data/corpora/embeddings.npz
(agents-corpus-index.md §2 / step 10, BUILD_INDEX.md §2).

Reads app/data/corpora/*.json, embeds each chunk's text with EMBED_MODEL (model2vec
static), and writes a single npz keyed by chunk_id to CORPORA_DIR/embeddings.npz — the
exact path index._build_matrix() reads — so startup loads the cache instead of
re-embedding (index-once-before-demo, spec §9). Run once before the demo:

    cd backend && python -m scripts.build_embeddings
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `app` importable when run as a plain script from anywhere.
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def build_embeddings() -> None:
    """Read corpora, embed every chunk, write data/corpora/embeddings.npz by chunk_id."""
    import numpy as np

    from app.agents.corpus import CORPORA_DIR, load_corpus_chunks
    from app.agents.embeddings import embed_texts

    vectors: dict[str, "np.ndarray"] = {}
    for path in sorted(CORPORA_DIR.glob("*.json")):
        agent_id = path.stem
        chunks = load_corpus_chunks(agent_id)  # asserts owner == agent_id (isolation)
        if not chunks:
            continue
        mats = embed_texts([c["text"] for c in chunks])
        for chunk, vec in zip(chunks, mats):
            vectors[chunk["chunk_id"]] = vec.astype("float32")
        print(f"  {agent_id}: embedded {len(chunks)} chunks")

    out = CORPORA_DIR / "embeddings.npz"
    np.savez(out, **vectors)
    print(f"wrote {len(vectors)} embeddings -> {out}")


if __name__ == "__main__":
    build_embeddings()
