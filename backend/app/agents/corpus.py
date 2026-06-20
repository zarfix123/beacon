"""Corpus load helpers + isolation assert (agents-corpus-index.md §2.3).

Responsibility (BUILD_INDEX.md §2.1): corpus load helpers ONLY. The AgentIndex
dataclass, `load_agent_index`, and the `set_visibility` mutator live in index.py;
this module holds the seed-reading helpers index.py/registry.py call.
"""
from __future__ import annotations

import json
import pathlib

from app.models import Chunk

SEED_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
CORPORA_DIR = SEED_DIR / "corpora"


def load_corpus_chunks(agent_id: str) -> list[Chunk]:
    """Read app/data/corpora/<agent_id>.json into a list of Chunk dicts.

    Asserts the isolation invariant: every row's `owner == agent_id`. Does NOT
    attach embeddings (that is index.py's job in cosine mode).
    """
    path = CORPORA_DIR / f"{agent_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks: list[Chunk] = data.get("chunks", [])
    assert_isolation(agent_id, chunks)
    return chunks


def assert_isolation(agent_id: str, chunks: list[Chunk]) -> None:
    """Raise if any chunk's `owner != agent_id` (spec §6 isolation guarantee)."""
    bad = [c.get("chunk_id") for c in chunks if c.get("owner") != agent_id]
    if bad:
        raise AssertionError(
            f"isolation violation: {agent_id} corpus contains chunks not owned by it: {bad}"
        )
