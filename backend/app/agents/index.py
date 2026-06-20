"""AgentIndex: one agent's isolated flat index (agents-corpus-index.md §2.3,
grant-access.md §2.4).

Responsibility (BUILD_INDEX.md §2.1): holds `AgentIndex` + `load_agent_index` +
`set_visibility` (the grant_access mutator). Each AgentIndex is a SEPARATE object
holding a SEPARATE chunk list — no agent references another's chunks/matrix (the
isolation guarantee, spec §6). This is a SKELETON — no logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

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
        # TODO: assert all(c["owner"] == self.agent_id for c in self.chunks)
        pass

    def set_visibility(self, chunk_id: str, visibility: Visibility) -> Visibility:
        """Mutate the stored visibility of one chunk in place (grant_access mutator).

        Resolves the row by globally-unique chunk_id; mutates ONLY that row;
        `embedding`/`text`/`doc_title`/`owner` untouched. Raises ChunkNotFoundError
        on miss. Returns the new visibility.
        """
        raise NotImplementedError("AgentIndex.set_visibility is a skeleton stub")


def load_agent_index(agent_id: str, *, with_embeddings: bool) -> AgentIndex:
    """Build one agent's isolated index from its seed corpus.

    with_embeddings=False -> stub mode (keyword overlap, matrix=None).
    with_embeddings=True  -> load data/embeddings.npz cache (or embed on miss) and
                             attach the matrix in chunks order.
    The returned AgentIndex contains ONLY rows whose owner == agent_id (enforced).
    """
    raise NotImplementedError("load_agent_index is a skeleton stub")
