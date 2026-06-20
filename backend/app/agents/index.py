"""AgentIndex: one agent's isolated flat index (agents-corpus-index.md §2.3,
grant-access.md §2.4).

Responsibility (BUILD_INDEX.md §2.1): holds `AgentIndex` + `load_agent_index` +
`set_visibility` (the grant_access mutator). Each AgentIndex is a SEPARATE object
holding a SEPARATE chunk list — no agent references another's chunks/matrix (the
isolation guarantee, spec §6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from app.agents.corpus import CORPORA_DIR, load_corpus_chunks
from app.models import Chunk, Visibility

if TYPE_CHECKING:
    import numpy as np


class ChunkNotFoundError(KeyError):
    """Raised by set_visibility when chunk_id is unknown (-> 404 upstream)."""


@dataclass
class AgentIndex:
    """One agent's isolated flat index. Holds ONLY this agent's chunks.

    `matrix` is the (n, EMBED_DIM) embedding matrix in `chunks` order (row i <->
    chunks[i]); None in stub mode. `__post_init__` asserts the isolation invariant
    (every row's owner == agent_id).
    """
    agent_id: str
    chunks: list[Chunk]
    matrix: Optional["np.ndarray"] = None

    def __post_init__(self) -> None:
        bad = [c["chunk_id"] for c in self.chunks if c["owner"] != self.agent_id]
        if bad:
            raise AssertionError(
                f"isolation violation: AgentIndex({self.agent_id}) holds foreign chunks: {bad}"
            )

    def set_visibility(self, chunk_id: str, visibility: Visibility) -> Visibility:
        """Mutate the stored visibility of one chunk in place (grant_access mutator).

        Resolves the row by globally-unique chunk_id; mutates ONLY that row;
        `embedding`/`text`/`doc_title`/`owner` untouched. Raises ChunkNotFoundError
        on miss. Returns the new visibility.
        """
        for c in self.chunks:
            if c["chunk_id"] == chunk_id:
                c["visibility"] = visibility
                return visibility
        raise ChunkNotFoundError(chunk_id)


def load_agent_index(agent_id: str, *, with_embeddings: bool) -> AgentIndex:
    """Build one agent's isolated index from its seed corpus.

    with_embeddings=False -> stub mode (keyword overlap, matrix=None).
    with_embeddings=True  -> load corpora/embeddings.npz cache (embed on miss) and
                             attach the matrix in chunks order.
    The returned AgentIndex contains ONLY rows whose owner == agent_id (enforced).
    """
    chunks = load_corpus_chunks(agent_id)
    matrix = _build_matrix(chunks) if with_embeddings else None
    return AgentIndex(agent_id=agent_id, chunks=chunks, matrix=matrix)


def _build_matrix(chunks: list[Chunk]) -> "np.ndarray":
    """Assemble the (n, EMBED_DIM) matrix in chunks order from the npz cache,
    embedding any chunk_id missing from the cache. Cosine-mode only (Phase 1.5)."""
    import numpy as np

    from app.agents.embeddings import EMBED_DIM, embed_texts

    npz_path = CORPORA_DIR / "embeddings.npz"
    cache: dict[str, "np.ndarray"] = {}
    if npz_path.exists():
        loaded = np.load(npz_path)
        cache = {key: loaded[key] for key in loaded.files}

    rows: list[Optional["np.ndarray"]] = []
    missing_idx, missing_texts = [], []
    for i, c in enumerate(chunks):
        cid = c["chunk_id"]
        if cid in cache:
            rows.append(cache[cid])
        else:
            rows.append(None)
            missing_idx.append(i)
            missing_texts.append(c["text"])

    if missing_texts:
        fresh = embed_texts(missing_texts)
        for j, i in enumerate(missing_idx):
            rows[i] = fresh[j]

    if not rows:
        return np.zeros((0, EMBED_DIM), dtype="float32")
    return np.vstack(rows).astype("float32")
