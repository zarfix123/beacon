# BUILD: Redaction Claude Call (restricted tier)

> **Subsystem owner:** Dennis (backend). **Status:** design/plan — not an implementation.
> This is the index for the Anthropic API call that turns a `restricted` chunk into a
> safe one-line gist that conveys *that* a solution exists without leaking its content
> (spec section 11, "Redaction"). It is invoked **inside the responding agent's gate**,
> after retrieval and before anything crosses the cross-agent boundary.

This doc does not contradict any frozen contract. Where a contract is silent or a gap
exists, it is flagged under **Risks**, never patched with a conflicting shape.

---

## 1. Purpose and where it sits in the query flow

### What it does
For a chunk whose `visibility == "restricted"`, the gate must produce a `ResponseItem`
with `decision == "redacted"` whose `answer` is a **one-line gist** — enough to tell the
asker *that* this party has a solution (and to whom to send a `grant_access` request),
but containing **none of the restricted payload**. Spec section 11 calls this a "real
transform — content never crosses the boundary." That transform is a single Anthropic
API call: hand Claude the restricted `text`, get back a safe gist string.

### Where it sits (spec section 10, "Query flow")
The orchestrator fans out to each party agent (step 2). Inside each responding agent:

```
search(query, agent_id)            # step 3 — retrieve first (returns ALL tiers, gate-free)
        │  list[Chunk] (public | restricted | private), score-ordered
        ▼
gate.decide(chunk)                 # step 4 — gate second; map visibility -> decision
    ├─ visibility == public     → decision=full      → (verification pass, separate subsystem)
    ├─ visibility == restricted → decision=redacted   → REDACTION CALL  ◀── THIS SUBSYSTEM
    └─ visibility == private    → decision=denied      → answer=null, no payload, no call
        │
        ▼
ResponseItem  (answer = gist for redacted; raw text NEVER attached)
        │
        ▼
orchestrator collects → emits `response-item` WS event → synthesizes → `done`
```

**Ordering invariant (spec section 9, sections 3 & 6):** retrieve-first, gate-second. The
redaction call runs *strictly inside* the responding agent's gate path, before the
`ResponseItem` is constructed and before that item is handed back to the orchestrator. The
raw `Chunk.text` of a restricted chunk is read only within `redaction.redact()`; it is never
copied onto the `ResponseItem`, never serialized into a WS event, and never returned to the
asking agent. This is the structural guarantee that "a restricted payload physically cannot
leak through the chain."

### Contract anchor
Output of this subsystem is exactly the `redacted` `ResponseItem` shape from
`shared/contracts/data-model.md` section 4 and the `response-item` WS payload in
`api-websocket.md`:

```json
{
  "answer": "Northwind has a documented fix for servo jitter under load. Request access to view the resolution.",
  "source_party": "Northwind Robotics",
  "source_doc_title": "Servo Jitter Postmortem — Q1",
  "decision": "redacted",
  "verified": false
}
```
`verified` is always `false` for redacted items (nothing was verified — no content crossed).
`answer` is the **gist this subsystem produces**. `chunk_id` + `source_agent_id` are added
by the orchestrator/transport layer, not here.

---

## 2. Files / modules to create under `backend/app/`

All paths are chosen to avoid collision with sibling subsystems. By convention this package
splits LLM calls under `backend/app/claude/` (redaction here; verification and synthesis are
sibling modules owned within the same area), the gate under `backend/app/gate.py`, and shared
types under `backend/app/models.py`. This subsystem **creates** the first three files below
and **depends on** (does not own) the rest.

| Path | Owns? | Responsibility |
|------|-------|----------------|
| `backend/app/claude/__init__.py` | create | Package marker for the Claude-call modules. |
| `backend/app/claude/client.py` | create (shared) | Singleton Anthropic client + model-id constants + a thin `complete_text()` helper used by redaction, verification, and synthesis. Centralizes API key handling, timeouts, retries, refusal handling. |
| `backend/app/claude/redaction.py` | **create (this subsystem)** | The redaction transform: `redact(chunk) -> str` (the gist) plus prompt construction, output validation/leak-guard, and an in-process cache. |
| `backend/app/gate.py` | depend (gate subsystem) | Calls `redaction.redact()` when `decision == "redacted"`. Owns visibility→decision mapping and `ResponseItem` assembly. |
| `backend/app/models.py` | depend (data-model) | `Chunk`, `ResponseItem` TypedDicts/dataclasses matching frozen contracts. |
| `backend/app/config.py` | depend (scaffold) | Env/settings: `ANTHROPIC_API_KEY`, model ids, feature flags. |

> If the team prefers a flat layout, `redaction.py` and `client.py` can live directly under
> `backend/app/` — but keep redaction in its **own module** so the gate imports a narrow
> surface (`from app.claude.redaction import redact`) and the leak-guard lives in one place.

### 2.1 `backend/app/claude/client.py` — shared client (sketch)

```python
"""Shared Anthropic client + thin text-completion helper.

Reused by redaction, verification, and synthesis so model id, timeouts,
retries, and refusal handling live in exactly one place.
"""
from __future__ import annotations
import anthropic
from app.config import settings

# Spec section 11 asks for redaction/verification/synthesis quality.
# Redaction is a SHORT, high-stakes transform (a leak here defeats the whole product),
# so it runs on the strong model. See section 4 for the model-choice rationale.
REDACTION_MODEL: str = "claude-opus-4-8"

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Process-wide singleton. Resolves ANTHROPIC_API_KEY from the env."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


def complete_text(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 128,
    cache_system: bool = True,
) -> str | None:
    """One-shot text completion. Returns the first text block, or None on refusal.

    - Adaptive thinking is OFF (omit `thinking`): redaction is a short, mechanical
      transform; thinking adds latency for no quality gain at this size.
    - `system` is cached (prefix is byte-stable across all redaction calls).
    - Returns None when stop_reason == "refusal" so the caller can fail safe.
    """
    client = get_client()
    system_blocks = [{"type": "text", "text": system}]
    if cache_system:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        return None
    return next((b.text for b in resp.content if b.type == "text"), None)
```

### 2.2 `backend/app/claude/redaction.py` — the subsystem (sketch)

```python
"""Restricted-chunk redaction (spec section 11).

Public surface used by the gate:

    redact(chunk: Chunk) -> str   # returns the safe one-line gist

The raw `chunk["text"]` is read ONLY inside this module. The returned gist is the
only thing that leaves; the caller (gate) attaches it to a `redacted` ResponseItem.
"""
from __future__ import annotations
from app.models import Chunk
from app.claude.client import complete_text, REDACTION_MODEL

# ── Prompt (tight; see section 3 for the full sketch + rationale) ──────────────
_SYSTEM = (
    "You are a permission gate for a knowledge-brokering network. You receive ONE "
    "internal document excerpt that the owner has marked RESTRICTED. Produce a single "
    "sentence that states ONLY that the owner has a documented solution/answer for the "
    "topic, so a requester knows it exists and can ask for access. "
    "HARD RULES: Reveal NO part of the actual solution — no root causes, fixes, numbers, "
    "parameters, code, names, configs, or specific techniques. Describe the TOPIC at the "
    "same level as a public title, never the resolution. One sentence, <= 25 words, no "
    "newlines, no quotes, no preamble. End by inviting an access request."
)

# Deterministic fallback if the model is unavailable or output fails the leak-guard.
def _safe_fallback(chunk: Chunk) -> str:
    party_topic = chunk["doc_title"]  # doc_title is itself owner-published metadata, safe to echo
    return (
        f'This party has a restricted document related to "{party_topic}". '
        "Request access to view the resolution."
    )

# In-process cache: same chunk text -> same gist (keyed by chunk_id + a hash of text,
# so a grant_access toggle that changes visibility does NOT serve a stale gist for a
# chunk whose text was edited during seeding). Cleared on process restart.
_cache: dict[str, str] = {}


def redact(chunk: Chunk) -> str:
    """Return a safe one-line gist for a RESTRICTED chunk. Never returns chunk text."""
    assert chunk["visibility"] == "restricted", "redact() is only for restricted chunks"

    key = _cache_key(chunk)
    if key in _cache:
        return _cache[key]

    user = (
        f"TOPIC (owner-published title, safe to reference): {chunk['doc_title']}\n"
        f"RESTRICTED EXCERPT (do NOT reveal any of this content):\n{chunk['text']}"
    )
    gist = complete_text(model=REDACTION_MODEL, system=_SYSTEM, user=user, max_tokens=80)

    if gist is None or not _passes_leak_guard(gist, chunk):
        gist = _safe_fallback(chunk)

    gist = _normalize(gist)
    _cache[key] = gist
    return gist


def _cache_key(chunk: Chunk) -> str:
    import hashlib
    h = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()[:16]
    return f"{chunk['chunk_id']}:{h}"


def _normalize(gist: str) -> str:
    """One line, trimmed, no surrounding quotes."""
    return " ".join(gist.split()).strip().strip('"').strip()


def _passes_leak_guard(gist: str, chunk: Chunk) -> bool:
    """Cheap deterministic backstop against verbatim leakage.

    The prompt is the primary defense; this catches gross failures:
    - reject if the gist contains a long verbatim run from the restricted text
    - reject if the gist is suspiciously long (the model dumped content)
    Returns False -> caller uses the deterministic safe fallback.
    """
    if len(gist) > 240:
        return False
    return not _shares_long_ngram(gist.lower(), chunk["text"].lower(), n=6)


def _shares_long_ngram(a: str, b: str, *, n: int) -> bool:
    """True if a and b share any contiguous run of >= n words (verbatim leak signal)."""
    bw = b.split()
    grams = {" ".join(bw[i : i + n]) for i in range(max(0, len(bw) - n + 1))}
    aw = a.split()
    return any(" ".join(aw[i : i + n]) in grams for i in range(max(0, len(aw) - n + 1)))
```

### 2.3 How the gate calls it (illustrative — gate is a sibling subsystem)

```python
# backend/app/gate.py  (NOT owned here; shown for the integration contract)
from app.claude.redaction import redact
from app.models import Chunk, ResponseItem

def decide(chunk: Chunk, party_name: str) -> ResponseItem:
    vis = chunk["visibility"]
    if vis == "public":
        # decision=full; verification pass attaches the verified answer (other subsystem)
        ...
    elif vis == "restricted":
        gist = redact(chunk)                       # ◀── redaction call, inside the agent
        return ResponseItem(
            answer=gist,                            # gist only; chunk["text"] NEVER attached
            source_party=party_name,
            source_doc_title=chunk["doc_title"],
            decision="redacted",
            verified=False,                         # nothing crossed -> always False
        )
    else:  # private
        return ResponseItem(
            answer=None, source_party=party_name, source_doc_title=None,
            decision="denied", verified=False,
        )
```

---

## 3. The Claude call

### Purpose
Transform one restricted chunk's `text` into a safe one-line gist (spec section 11).

### Model choice
**`claude-opus-4-8`.** Rationale: redaction is *short* (input is one chunk, output is one
sentence) but **high-stakes** — a single leaked clause defeats the product's core wedge
("enforced permission at the owner's boundary"). The cost per call is tiny (tens of input
tokens, <80 output tokens), so the cheaper `claude-haiku-4-5` saves almost nothing in
absolute terms while raising the risk of a subtle leak under adversarial chunk text. Spec
section 11 explicitly asks for redaction/verification/synthesis *quality*. Keep all three on
`claude-opus-4-8` for the MVP/demo; revisit Haiku only if redaction latency becomes a
demo-visible bottleneck (it won't, at 3 agents × tiny corpora).

### Request parameters
- `model="claude-opus-4-8"`
- `max_tokens=80` (one short sentence; hard ceiling so a misbehaving response can't dump text)
- **No `thinking`** (omit it): mechanical short transform; adaptive thinking only adds latency.
- **No sampling params** (`temperature`/`top_p`/`top_k`) — removed on Opus 4.8; sending any 400s.
- `system` carried as a cached text block (`cache_control: {"type": "ephemeral"}`); the system
  prompt is byte-stable across every redaction call, so it caches after the first call.

### Tight prompt sketch
**System** (frozen, cached):
```
You are a permission gate for a knowledge-brokering network. You receive ONE internal
document excerpt that the owner has marked RESTRICTED. Produce a single sentence that
states ONLY that the owner has a documented solution/answer for the topic, so a requester
knows it exists and can ask for access.
HARD RULES:
- Reveal NO part of the actual solution: no root causes, fixes, numbers, parameters,
  code, configuration values, proper names, or specific techniques.
- Describe the TOPIC at the level of a public title, never the resolution.
- Exactly one sentence, <= 25 words, no newlines, no quotation marks, no preamble.
- End by inviting an access request.
```
**User** (per call):
```
TOPIC (owner-published title, safe to reference): {doc_title}
RESTRICTED EXCERPT (do NOT reveal any of this content):
{chunk.text}
```

### Expected output shape (spec section 11)
A **plain string** — one sentence, the gist. Example for the locked demo chunk:
```
Northwind has a documented fix for servo jitter under sustained load. Request access to view the resolution.
```
That string becomes `ResponseItem.answer` for the `redacted` item. No JSON, no structured
output needed — the contract field is a single string. (Structured output is deliberately
avoided here: it adds a schema-compile round-trip and the payload is one short string.)

### Why this guarantees the raw text never crosses the boundary
1. `chunk["text"]` is referenced **only** in `redact()` (and the leak-guard), both inside the
   responding agent's process, inside the gate path.
2. `redact()` returns a *new* string (the gist or the deterministic fallback) — never the
   input text.
3. The gate attaches that string to `ResponseItem.answer`; the orchestrator and WS layer only
   ever see the `ResponseItem`, which by construction has no `text` field.
4. The leak-guard (`_passes_leak_guard`) is a deterministic backstop: if the model output
   shares a long verbatim run with the source, the call falls back to a content-free template.
5. `embedding` is already excluded by the data-model contract; `text` exclusion is enforced
   here.

---

## 4. Caching

- **Prompt cache (Anthropic-side):** the `system` prompt is a stable prefix → mark it
  `cache_control: {"type": "ephemeral"}`. After the first redaction call, subsequent calls in
  the same 5-minute window pay ~0.1× on the system tokens. (Note: the system block alone is
  small; this is a latency/cost nicety, not load-bearing for the demo.)
- **Result cache (in-process):** `redaction.py._cache` maps `chunk_id + sha256(text)[:16]` →
  gist. The locked demo re-runs the *same* query (and the `grant_access` re-run re-runs it
  again), so a given restricted chunk is redacted at most once per process. Keying on a hash
  of `text` (not just `chunk_id`) means the cache self-invalidates if a chunk's text changes
  during seeding, and is irrelevant after a `grant_access` toggle because the chunk is then
  `public` (the gate stops calling `redact()` for it entirely).
- **Cache is cleared on process restart** — acceptable for the MVP (in-process, single
  service, spec section 5).

---

## 5. Dependencies

### Backend modules
- `app.models` — `Chunk`, `ResponseItem` (frozen data-model shapes). Consumed, not owned.
- `app.config` — `settings.ANTHROPIC_API_KEY` and model ids. Consumed.
- `app.claude.client` — shared Anthropic client + `complete_text()`. **Created here, shared**
  with verification and synthesis subsystems.
- `app.gate` — the caller. Owned by the gate subsystem; this doc only specifies the call site.

### pip packages
- `anthropic` (official SDK — required; the call is `client.messages.create(...)`).
- `fastapi`, `uvicorn` (service host — already a project dependency; not specific to redaction).
- stdlib only otherwise (`hashlib`, `functools` if a decorator cache is preferred).
- No extra retrieval/embedding deps — redaction never touches `embedding` or `search()`.

`ANTHROPIC_API_KEY` must be present in the environment (no prod auth otherwise, per spec
section 5).

---

## 6. Ordered build steps

1. **Scaffold the package.** Create `backend/app/claude/__init__.py`. Confirm `app.models`
   exposes `Chunk` and `ResponseItem` matching the frozen data-model (coordinate with the
   data-model/scaffold owner — do not redefine).
2. **Add `client.py`.** Implement `get_client()` (singleton) and `complete_text()` with
   `model`, `system` (cached block), `user`, `max_tokens`, refusal-returns-`None`. Add the
   `REDACTION_MODEL = "claude-opus-4-8"` constant.
3. **Write the system prompt** in `redaction.py` (the section-3 sketch). Keep it frozen and
   byte-stable (so the prompt cache works).
4. **Implement `redact(chunk)`** building the per-call user message from `doc_title` + `text`,
   calling `complete_text(max_tokens=80)`.
5. **Implement the leak-guard** (`_passes_leak_guard`, `_shares_long_ngram`) and the
   deterministic `_safe_fallback`. Wire the fallback for both `gist is None` (refusal /
   unavailable) and leak-guard failure.
6. **Implement `_normalize`** (single line, trim, strip quotes) and the in-process `_cache`
   keyed on `chunk_id + sha256(text)`.
7. **Unit-test against the stub corpus.** Using the keyword `search()` stub (search-interface
   contract), pull the seeded *restricted* chunk for the locked demo query and assert:
   (a) `redact()` returns a non-empty one-line string ≤ ~240 chars;
   (b) the gist shares no ≥6-word run with `chunk["text"]` (leak-guard passes);
   (c) the gist is deterministic across two calls (cache hit, identical output);
   (d) with the API key unset / forced refusal, `redact()` returns the safe fallback (no raw text).
8. **Integration smoke test with the gate.** Have `gate.decide()` call `redact()` for the
   restricted chunk and assert the emitted `ResponseItem` has `decision="redacted"`,
   `verified=False`, `answer == gist`, and **no** `text`/`embedding` keys anywhere on the item.
9. **(Optional) verify prompt-cache hits** by logging `usage.cache_read_input_tokens` on the
   second redaction call (expect > 0).

---

## 7. Integration points with frozen contracts and other subsystems

- **`data-model.md` section 2 (Chunk):** input is a `Chunk`; this subsystem reads `visibility`
  (must be `restricted`), `text` (the payload to redact — never re-emitted), and `doc_title`
  (safe topic label). It never reads or emits `embedding`.
- **`data-model.md` section 4 (ResponseItem):** output gist becomes `answer`; `decision` is
  fixed to `"redacted"` and `verified` to `false` by the gate. The five canonical fields are
  produced by the gate using this gist — shapes are not altered here.
- **`search-interface.md`:** redaction runs *after* `search()` (retrieve-first). It relies on
  the stub guarantee that the locked demo query returns at least one `restricted` chunk on one
  party, so the redaction path and the `grant_access` hero beat are exercisable before Hao's
  real retrieval lands at H8. No call into `search()` from this module.
- **`api-websocket.md` (`response-item` event):** the gist is the `answer` field of the
  `redacted` `response-item` frame; `chunk_id` + `source_agent_id` are added by the
  orchestrator/transport, enabling the frontend "Request access from [Party]" button. This
  module does not emit WS frames.
- **`grant_access` (`api-websocket.md`):** when the chunk's visibility is toggled
  `restricted → public` and the query re-runs, the gate routes that chunk to the `full` path
  (not `redacted`), so `redact()` is **not** called on the re-run — the card flips from gist
  to verified answer. No grant-access logic lives here; this subsystem simply isn't invoked
  for the now-public chunk.
- **Gate subsystem:** sole caller. Contract is the narrow `redact(chunk: Chunk) -> str`.
- **Verification subsystem (sibling):** shares `app.claude.client`. Redaction items are never
  verified (`verified=False`), so the two never interact on the same item.
- **Synthesis subsystem (sibling):** consumes the `redacted` `ResponseItem` (and `done`
  provenance) but only the gist string, never the raw text.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **Leakage** — the model echoes part of the restricted text into the gist. | Primary: a strict system prompt with explicit HARD RULES + `max_tokens=80` ceiling. Backstop: deterministic `_passes_leak_guard` rejects any output sharing a ≥6-word verbatim run with the source (or > 240 chars) and substitutes a content-free template. `redact()` provably never returns `chunk["text"]`. |
| **Boundary breach** — raw text crosses the agent boundary another way. | `text` is read only inside `redact()`; the gate attaches *only* the returned gist to `ResponseItem`. `embedding`/`text` are not fields on `ResponseItem`, so no WS frame can carry them. Add the integration assertion in build step 8 to lock this in. |
| **Latency** — extra Claude call per restricted chunk on the live demo. | Tiny input/output; in-process result cache means each restricted chunk is redacted at most once per process; prompt-cache on the system block; corpora are tiny (spec section 17). The `grant_access` re-run does NOT re-redact (chunk is now public). |
| **Isolation** — redaction reaching into another agent's data. | `redact()` operates on a single `Chunk` already scoped to the responding agent by `search()` (owner == agent_id). It makes no cross-agent lookups. |
| **API unavailability / refusal** — Opus call fails or returns `stop_reason: "refusal"`. | `complete_text()` returns `None` on refusal; `redact()` falls back to the deterministic `_safe_fallback`, which is content-free and still satisfies the `redacted` contract. SDK auto-retries 429/5xx. The demo never hard-fails on a missing gist. |
| **Over-redaction** — gist too vague to be compelling on stage. | The user message passes `doc_title` (owner-published, safe) so the gist can name the *topic* ("servo jitter under load") without the resolution — matching the demo card copy. Tune the prompt against the locked demo chunk in build step 7. |
| **Contract gap (noted, not patched):** the data-model marks `text` as "never leaves the owning agent for restricted/private," but does not specify *where* the gate reads it. | Documented here that `text` is read solely inside `redact()` within the responding agent. No shape change; this is the enforcement locus the contracts delegate to "the backend gate." If the team wants this written into a contract, that is a 2-minute sync, not a unilateral edit. |
| **Non-determinism across runs** could make the demo look flaky. | In-process cache makes a given chunk's gist stable within a process; `_normalize` removes whitespace/quote variation. For a fully reproducible rehearsal, the `_safe_fallback` path is deterministic and can be forced via a config flag if desired (flag lives in `config.py`, not invented in a contract). |
