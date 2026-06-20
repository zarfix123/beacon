"""Tests for app/models.py (BUILD_INDEX.md §2 / step 2).

Phase 1 scope: the frozen Chunk / ResponseItem key sets and the shared enum values.
(The `GatedResult.to_wire()` 7-key emitter test is Phase 2 — `to_wire` is an
intentional NotImplementedError stub until the gate is built.)
"""
from __future__ import annotations

from typing import get_args

from app.models import Chunk, Decision, GateDecision, ResponseItem, Visibility


def test_visibility_literal_values():
    assert set(get_args(Visibility)) == {"public", "restricted", "private"}


def test_decision_literal_values():
    assert set(get_args(Decision)) == {"full", "redacted", "denied"}


def test_gate_decision_enum_matches_decision():
    assert {d.value for d in GateDecision} == {"full", "redacted", "denied"}


def test_chunk_required_keys():
    # embedding/score are NotRequired — a Chunk is constructible without them.
    chunk: Chunk = {
        "chunk_id": "a_c000",
        "parent_doc_id": "a_d00",
        "doc_title": "Title",
        "owner": "agent_a",
        "visibility": "public",
        "text": "body",
    }
    assert set(chunk) == {
        "chunk_id", "parent_doc_id", "doc_title", "owner", "visibility", "text",
    }


def test_response_item_keys():
    item: ResponseItem = {
        "answer": "a",
        "source_party": "Party",
        "source_doc_title": "Title",
        "decision": "full",
        "verified": True,
        "chunk_id": "a_c000",
        "source_agent_id": "agent_a",
    }
    # exactly the 5 canonical fields + 2 transport ids; no embedding / text.
    assert set(item) == {
        "answer", "source_party", "source_doc_title", "decision", "verified",
        "chunk_id", "source_agent_id",
    }
