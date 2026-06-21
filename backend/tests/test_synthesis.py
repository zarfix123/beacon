"""Tests for app/claude/synthesis.py + the synthesis prompt (leakage-safe, fail-soft)."""
from __future__ import annotations

from app.claude.prompts import synthesis_user
from app.claude.synthesis import _EMPTY, synthesize


def _item(party, title, answer, decision="full", verified=True, cid="c", aid="a"):
    return {"answer": answer, "source_party": party, "source_doc_title": title,
            "decision": decision, "verified": verified, "chunk_id": cid, "source_agent_id": aid}


async def test_empty_input_returns_graceful_no_claude():
    # No patch_claude installed: if this touched the network it would error.
    assert await synthesize("q", [], []) == _EMPTY


async def test_cites_by_index(patch_claude):
    patch_claude(text="Clamp the integral term [1].")
    out = await synthesize("how to fix servo", [_item("Party A", "Servo Fix", "clamp the integral term")], [])
    assert "[1]" in out


async def test_prompt_numbering_continues_for_restricted():
    user = synthesis_user(
        query="q",
        verified_facts=[{"source_party": "A", "source_doc_title": "T", "answer": "fact"}],
        redacted=[{"source_party": "B", "source_doc_title": "Throttle Config"}],
    )
    assert "[1]" in user and "[2]" in user          # restricted item continues the numbering
    assert "Throttle Config" in user                 # doc title is safe to name


async def test_synthesize_omits_restricted_payload(patch_claude):
    # The restricted gist/content must NEVER reach the synthesis prompt.
    client = patch_claude(text="answer [1].")
    redacted = _item("B", "Secret Postmortem", "THE SECRET ROOT CAUSE WAS WINDUP",
                     decision="redacted", verified=False)
    await synthesize("q", [_item("A", "T", "public fact")], [redacted])
    sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "THE SECRET ROOT CAUSE" not in sent       # payload withheld
    assert "Secret Postmortem" in sent               # but its existence (title) is surfaced


async def test_refusal_falls_back(patch_claude):
    patch_claude(text=None, stop_reason="refusal")
    out = await synthesize("q", [_item("Party A", "T", "fact")], [])
    assert "could not be composed" in out and "Party A" in out
