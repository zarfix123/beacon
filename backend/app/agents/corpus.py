"""Corpus load helpers + isolation assert (agents-corpus-index.md §2.3).

Responsibility (BUILD_INDEX.md §2.1): corpus load helpers ONLY. The AgentIndex
dataclass, `load_agent_index`, and the `set_visibility` mutator live in index.py;
this module holds the seed-reading helpers index.py/registry.py call. This is a
SKELETON — no logic.
"""
from __future__ import annotations

import pathlib

from app.models import Chunk

SEED_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
CORPORA_DIR = SEED_DIR / "corpora"


def load_corpus_chunks(agent_id: str) -> list[Chunk]:
    """Read app/data/corpora/<agent_id>.json into a list of Chunk dicts.

    Asserts the isolation invariant: every row's `owner == agent_id`. Does NOT
    attach embeddings (that is index.py's job in cosine mode).
    """
    raise NotImplementedError("load_corpus_chunks is a skeleton stub")


def assert_isolation(agent_id: str, chunks: list[Chunk]) -> None:
    """Raise if any chunk's `owner != agent_id` (spec §6 isolation guarantee)."""
    raise NotImplementedError("assert_isolation is a skeleton stub")
