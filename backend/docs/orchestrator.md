# Beacon — Backend Subsystem BUILD doc: Orchestrator

> **Status: PLAN / INDEX (not an implementation).** Code blocks below are
> sketches and signatures, not finished functions. Owner: Dennis (backend).
> Aligns to spec sections 6, 9, 10, 11 and the three frozen contracts in
> `shared/contracts/`. Do not contradict those shapes; gaps are noted under
> Risks rather than reshaped here.

---

## 1. Purpose & where it sits in the query flow

The **Orchestrator** is the coordination core that lives *in the asking
agent* (spec section 6). It owns steps **2, 5, and 6** of the query loop
(spec section 10) and drives the rest:

```
spec §10 step          owner module                       this doc?
---------------------  ---------------------------------  --------------
1. user submits        api layer (POST /query, WS)        consumes us
2. embed + fan out  →  ORCHESTRATOR -> router             OWNED HERE
3. cosine top-k        search() (Hao) / stub (Dennis)     dependency
4. gate per chunk      gate + redaction (responder side)  dependency
5. collect + verify →  ORCHESTRATOR + verification        OWNED HERE
6. synthesize + cite →  ORCHESTRATOR + synthesis Claude    OWNED HERE
```

Position in the call graph (one run):

```
POST /query  or  WS {type:query}
        │
        ▼
  Orchestrator.run_query(req)                      ◄── entrypoint, async generator
        │  1. resolve asker, allocate query_id
        │  2. pick target party agents (the other 2)
        │  3. for each party: emit agent-activated  ──────► WS event
        │
        ├─► router.dispatch(CrossAgentRequest)  (in-process, concurrent)
        │        │
        │        ▼   *** runs INSIDE the responding agent (boundary) ***
        │     search(query, party_id, top_k)      ◄── retrieve FIRST (§9)
        │        │
        │        ▼
        │     gate.decide(chunk) -> full|redacted|denied   ◄── gate SECOND (§9, §6)
        │        │   restricted → redaction Claude call (gist; text never leaves)
        │        │   private    → denied (no payload crosses)
        │        ▼
        │     returns GatedItem(s)  ── only authorized content crosses back ──┐
        │                                                                     │
        ◄─────────────────────────────────────────────────────────────────  ┘
        │  4. per returned item: verification Claude call (full only)
        │     emit response-item                       ──────► WS event
        │
        │  5. synthesis Claude call over verified full items
        │     emit done {synthesized_answer, provenance, item_count}  ──► WS event
        ▼
   final assembled FinalResponse (also returned to caller)
```

The **hard ordering guarantee** the orchestrator must preserve: it never
sees raw `restricted`/`private` chunk `text`. The gate + redaction run on the
*responder* side of the router boundary and hand back a `GatedItem` whose
`answer` is already safe (full text for public, one-line gist for restricted,
`null` for denied). The orchestrator's verification and synthesis only ever
operate on content the gate already cleared. This is the wedge (spec §3, §6)
and the reason the gate cannot live in the orchestrator.

---

## 2. Files / modules to create under `backend/app/`

The orchestrator owns three files and **consumes** modules owned by the
sibling backend subsystems (router, gate, redaction, verification, search,
agents registry). Paths chosen to not collide with those subsystems.

```
backend/app/
├── orchestrator.py        ← OWNED: entrypoint, fan-out, collect, drive verify/synth
├── synthesis.py           ← OWNED: the synthesis Claude call + prompt
├── orchestrator_models.py ← OWNED: assembled shapes (FinalResponse, GatedItem, events)
│
├── router.py              ← dependency (sibling): in-process fan-out + WS emit
├── gate.py                ← dependency (sibling): visibility→decision, runs in responder
├── redaction.py           ← dependency (sibling): restricted-gist Claude call
├── verification.py        ← dependency (sibling): grounding Claude call
├── agents.py              ← dependency (sibling): Agent registry, party_name lookup
├── search.py              ← dependency (Hao/stub): search(query, agent_id, top_k)
└── llm.py                 ← dependency (sibling): shared Anthropic client + model ids
```

> Naming note: the orchestrator deliberately uses `orchestrator_models.py`
> (not a generic `models.py` or `schemas.py`) so it cannot collide with an
> API-layer `schemas.py` or a shared `models.py` another subsystem may claim.
> Wire-facing DTOs (POST/WS request+response bodies) belong to the API
> subsystem; this file holds only the *internal assembled* shapes the
> orchestrator produces/consumes.

### 2.1 `orchestrator_models.py` — assembled shapes

Internal dataclasses/Pydantic models. The **wire shapes are frozen** by the
contracts; these are the in-process representations the orchestrator builds
before the API layer serializes them. Field names match the contracts so
serialization is a near-passthrough.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional

Decision = Literal["full", "redacted", "denied"]
Visibility = Literal["public", "restricted", "private"]


@dataclass
class GatedItem:
    """What a responding agent hands back across the router boundary,
    AFTER retrieve→gate→(redact). `answer` is already safe: full text
    for public, one-line gist for restricted, None for denied.
    `text` raw payload is intentionally absent — it never crosses.
    Pre-verification: `verified` is filled in by the orchestrator."""
    chunk_id: str
    source_agent_id: str          # chunk owner == the responding party id
    source_party: str             # party_name resolved on responder side
    source_doc_title: Optional[str]
    decision: Decision
    answer: Optional[str]
    score: float                  # carried for synthesis ranking; not serialized
    verified: bool = False        # set by verification pass (full only)


@dataclass
class ResponseItem:
    """The frozen response-item / provenance shape (data-model §4 + the two
    transport ids). Built from a GatedItem after verification. Exactly the
    fields the WS `response-item` event serializes."""
    answer: Optional[str]
    source_party: str
    source_doc_title: Optional[str]
    decision: Decision
    verified: bool
    chunk_id: str                 # transport addition (grant-access handle)
    source_agent_id: str          # transport addition (owning agent id)

    def to_event(self, query_id: str) -> dict:
        """Shape the `response-item` WS frame (api-websocket.md)."""
        ...


@dataclass
class FinalResponse:
    """The assembled result of one run. Drives the `done` WS event and is
    also returned from run_query for non-WS callers / tests."""
    query_id: str
    from_agent: str
    synthesized_answer: str
    provenance: list[ResponseItem]   # full/redacted contributors
    items: list[ResponseItem]        # every emitted response item
    item_count: int                  # == len(items); sanity check for client

    def to_done_event(self) -> dict:
        """Shape the `done` WS frame (api-websocket.md)."""
        ...
```

### 2.2 `orchestrator.py` — entrypoint + loop

Owns the fan-out/collect/verify/synthesize sequence. Emits WS events through
an injected sink so it is transport-agnostic and unit-testable.

```python
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable, Optional

from .orchestrator_models import GatedItem, ResponseItem, FinalResponse
from .agents import Agent, get_agent, list_party_agents
from . import router, verification, synthesis

# An event sink the API/WS layer provides; in tests, a list-collector.
EventSink = Callable[[dict], Awaitable[None]]


class Orchestrator:
    def __init__(
        self,
        emit: EventSink,
        *,
        top_k: int = 5,
        verify_concurrency: int = 3,
    ) -> None:
        self._emit = emit
        self._top_k = top_k
        self._sem = asyncio.Semaphore(verify_concurrency)

    async def run_query(
        self,
        query: str,
        from_agent: Optional[str] = None,
        *,
        query_id: Optional[str] = None,
    ) -> FinalResponse:
        """Entrypoint. Plan → fan out → collect → verify → synthesize.
        Emits agent-activated*, response-item*, then one done event.
        Returns the assembled FinalResponse (callers may ignore it and
        just consume the streamed events)."""
        asker = resolve_asker(from_agent)              # default demo asker if None
        query_id = query_id or new_query_id()          # "q_" + short hash
        parties: list[Agent] = list_party_agents(exclude=asker.id)

        # 1. announce fan-out: one agent-activated per party (drives node pulse)
        await asyncio.gather(*(
            self._emit(agent_activated_event(query_id, p)) for p in parties
        ))

        # 2. fan out concurrently; each party retrieves→gates on ITS side
        gated: list[GatedItem] = await self._fan_out(query, parties)

        # 3. collect → verify (full only) → emit one response-item per item
        items: list[ResponseItem] = await self._resolve_items(query, query_id, gated)

        # 4. synthesize a cited answer over verified full items, emit done
        return await self._finish(query, query_id, asker.id, items)

    async def _fan_out(self, query: str, parties: list[Agent]) -> list[GatedItem]:
        """Dispatch the CrossAgentRequest to every party via the router,
        concurrently. The router calls search()→gate()→(redaction) on the
        responder side and returns GatedItems. The orchestrator NEVER calls
        search/gate directly — that keeps enforcement at the owner boundary."""
        results = await asyncio.gather(*(
            router.dispatch(from_query=query, to_agent=p.id, top_k=self._top_k)
            for p in parties
        ), return_exceptions=True)
        return flatten_ok(results)     # log+drop per-party failures (§ Risks)

    async def _resolve_items(
        self, query: str, query_id: str, gated: list[GatedItem]
    ) -> list[ResponseItem]:
        """For each gated item: verify full items (gist/denied skip verify),
        build the frozen ResponseItem, emit the response-item event as soon
        as it resolves (any order across parties)."""
        async def one(g: GatedItem) -> ResponseItem:
            if g.decision == "full" and g.answer:
                async with self._sem:
                    g.verified = await verification.verify(
                        answer=g.answer, query=query,
                        chunk_id=g.chunk_id, agent_id=g.source_agent_id,
                    )
            item = to_response_item(g)            # verified stays False for redacted/denied
            await self._emit(item.to_event(query_id))
            return item
        return list(await asyncio.gather(*(one(g) for g in gated)))

    async def _finish(
        self, query: str, query_id: str, from_agent: str, items: list[ResponseItem]
    ) -> FinalResponse:
        contributors = [i for i in items if i.decision in ("full", "redacted")]
        verified_full = [i for i in items if i.decision == "full" and i.verified]
        answer = await synthesis.synthesize(query=query, items=verified_full,
                                            redacted=[i for i in items if i.decision == "redacted"])
        final = FinalResponse(
            query_id=query_id, from_agent=from_agent,
            synthesized_answer=answer, provenance=contributors,
            items=items, item_count=len(items),
        )
        await self._emit(final.to_done_event())
        return final


# --- module-level helpers (sketched) -----------------------------------------
def resolve_asker(from_agent: Optional[str]) -> Agent: ...   # default demo asker
def new_query_id() -> str: ...                               # "q_" + 6 hex
def agent_activated_event(query_id: str, a: Agent) -> dict: ...
def to_response_item(g: GatedItem) -> ResponseItem: ...
def flatten_ok(results: list) -> list[GatedItem]: ...        # drop exceptions, log
```

**Re-run support (grant_access).** The `POST /grant_access` handler (API
subsystem) toggles the chunk visibility (gate/agents own the toggle), then
calls `run_query(...)` again **with the original `query` and `query_id`**.
The orchestrator is stateless per run, so re-running is just another
`run_query` with a known `query_id`. To support that, the API layer must
retain the original `(query, from_agent)` for each `query_id` (a small
in-memory `dict[str, tuple[str, str]]` — owned by the API/router subsystem,
noted under Integration so it is not duplicated here).

### 2.3 `synthesis.py` — the synthesis Claude call

```python
from __future__ import annotations
from .orchestrator_models import ResponseItem
from . import llm

async def synthesize(
    query: str,
    items: list[ResponseItem],       # verified == True, decision == full
    redacted: list[ResponseItem],    # restricted gists, to surface access asks
) -> str:
    """Compose the final cited answer from verified full items.
    Redacted items are surfaced as 'a fix exists at X, request access'
    WITHOUT inventing their content. Returns plain text with inline
    [Party] citations. Empty-input guard returns a graceful 'no verified
    answer' string (no Claude call)."""
    if not items and not redacted:
        return "No party returned a verified answer to this question."
    ...
```

See section 3 for the prompt sketch, model, and output shape.

---

## 3. Claude (Anthropic API) calls

This subsystem makes **one** Claude call directly (synthesis). It *triggers*
two more that are implemented in sibling modules (redaction on the responder
side, verification on collect) — documented here for completeness because the
orchestrator orders them and consumes their outputs (spec §11).

All calls go through a shared `llm.py` (sibling) that holds the
`anthropic.AsyncAnthropic` client, model-id constants, and a thin
`await llm.complete(model, system, user, max_tokens) -> str` helper with a
timeout + one retry. Keeping the client in one module avoids per-call
collisions across subsystems.

### 3.1 Synthesis (OWNED HERE)

- **Purpose:** turn the verified `full` response items into one cohesive,
  cited answer for the left panel; surface restricted items as access asks
  without leaking their content (spec §10 step 6, §12 synthesized-answer panel).
- **Model:** **`claude-opus-4-8`** — this is the user-facing deliverable, the
  thing on stage; synthesis quality + faithful citation matter most. Worth the
  top tier. (Verification and redaction below can stay opus for quality, but
  if latency bites, verification is the safe one to drop to
  `claude-haiku-4-5` — see Risks.)
- **Prompt sketch:**

  ```
  system:
    You are the asking agent in a permissioned knowledge network. You write
    ONE concise answer to the user's question, grounded ONLY in the supplied
    verified facts. Rules:
      - Use only the VERIFIED FACTS. Never add outside knowledge.
      - Cite each claim inline as [Party Name].
      - For RESTRICTED ITEMS, state that a relevant solution exists at that
        party and access can be requested. Do NOT invent its content.
      - If no verified facts are given, say no verified answer is available.
      - 2-5 sentences. No preamble.

  user:
    QUESTION: {query}

    VERIFIED FACTS:
    [1] ({source_party}, doc: {source_doc_title}) {answer}
    [2] ...

    RESTRICTED ITEMS (mention existence + access only, no content):
    - {source_party} (doc: {source_doc_title})
  ```

- **Expected output shape (spec §11):** plain text string (the
  `synthesized_answer`). No JSON — the provenance list is assembled
  deterministically by the orchestrator from the `ResponseItem`s, not parsed
  out of the model output. `max_tokens` ~300.

### 3.2 Redaction (triggered, implemented in `redaction.py`)

- **Purpose:** for a `restricted` chunk, produce a one-line gist that conveys
  *that* a solution exists without leaking the payload (spec §11). Runs on the
  responder side, inside the gate path, BEFORE crossing the boundary.
- **Model:** `claude-opus-4-8` (leakage-sensitive transform; quality matters,
  output is tiny so cost is negligible).
- **Output shape:** plain string → becomes `GatedItem.answer` for a `redacted`
  item (`verified=False`).
- **Orchestrator contract:** orchestrator never calls this; it only receives
  the already-redacted `answer`. Documented so ordering (redact-before-cross)
  is unambiguous.

### 3.3 Verification (triggered here, implemented in `verification.py`)

- **Purpose:** for each `full` item, confirm the returned answer is grounded
  in its cited source chunk; catches fabricated citations (spec §11, demo
  kicker §13.7).
- **Model:** **`claude-opus-4-8`** for grounding accuracy, but this is the
  **first call to downgrade to `claude-haiku-4-5`** if the loop is slow — it is
  a yes/no judgment on tiny inputs and haiku handles it well. Call it out in
  `llm.py` as a single swappable constant.
- **Signature (consumed by orchestrator):**

  ```python
  async def verify(*, answer: str, query: str, chunk_id: str, agent_id: str) -> bool: ...
  ```

  Verification re-reads the *raw* cited chunk on the responder side (it owns
  the text) — it does NOT receive raw text across the boundary; it receives
  identifiers and looks the chunk up locally. Returns `True`/`False`.
- **Prompt sketch:**

  ```
  system: You are a strict grounding checker. Answer ONLY "yes" or "no".
          "yes" iff the ANSWER is fully supported by the SOURCE. No explanation.
  user:   SOURCE: {chunk.text}
          ANSWER: {answer}
          Is the ANSWER supported by the SOURCE?
  ```

- **Output shape (spec §11):** map the model's `yes`/`no` to a `bool`
  (`verified ✓` / `unverifiable ✗`). Default to `False` on parse failure or
  timeout (fail-closed — an unverifiable claim must not show a checkmark).

---

## 4. Dependencies

### Backend modules (siblings; orchestrator imports them)

| Module | What the orchestrator uses |
|--------|----------------------------|
| `router.py` | `dispatch(from_query, to_agent, top_k) -> list[GatedItem]`. In-process fan-out boundary; runs search→gate→redaction on the responder side. The orchestrator's only door into other parties. |
| `gate.py` | The visibility→decision mapping + the `grant_access` visibility toggle. Orchestrator does not call it directly; the router does, behind the boundary. Listed because re-run depends on the toggle having happened. |
| `redaction.py` | `redact(chunk) -> str`. Called by the gate path, not the orchestrator. |
| `verification.py` | `verify(answer, query, chunk_id, agent_id) -> bool`. Called by `_resolve_items`. |
| `agents.py` | `Agent` model, `get_agent(id)`, `list_party_agents(exclude)`, `party_name` resolution. |
| `search.py` | `search(query, agent_id, top_k) -> list[Chunk]` (Hao's real impl or Dennis's stub). Called inside the router, not the orchestrator. |
| `llm.py` | Shared `AsyncAnthropic` client, model-id constants, `complete(...)` helper. Used by `synthesis.py`. |

### Pip packages

| Package | Why |
|---------|-----|
| `anthropic` | Claude API client (`AsyncAnthropic`). Synthesis call. |
| `fastapi` | App + the `/query`, `/grant_access`, `/ws/query` endpoints (API subsystem; orchestrator is invoked from there). |
| `uvicorn[standard]` | ASGI server (dev). |
| `pydantic` | If models use Pydantic instead of `@dataclass` (either is fine per contracts). |
| `numpy` *(transitive)* | Real `search()`/embeddings (Hao). Not imported by the orchestrator directly. |
| `chromadb` *(optional, transitive)* | Alt retrieval store (Hao). Not an orchestrator dep. |
| `pytest`, `pytest-asyncio` | Async unit tests for `run_query` against a fake event sink + fake router. |
| `python-dotenv` *(optional)* | Load `ANTHROPIC_API_KEY` in dev. |

`asyncio` is stdlib (fan-out + bounded verification concurrency).

---

## 5. Ordered build steps

1. **Scaffold `orchestrator_models.py`.** Define `GatedItem`, `ResponseItem`,
   `FinalResponse` with `to_event` / `to_done_event` matching the frozen WS
   shapes. Write a tiny test asserting the serialized dicts equal the example
   frames in `api-websocket.md` (response-item + done).
2. **Stub the sibling boundary.** Add a fake `router.dispatch` returning
   canned `GatedItem`s (one `full`, one `redacted`, one `denied`) for the
   locked demo query, and a fake `verification.verify` returning `True`. This
   unblocks the orchestrator before the gate/router are done (mirrors the
   spec §15 mock-driven approach).
3. **Implement `Orchestrator.run_query` happy path** against the fakes:
   resolve asker, allocate `query_id`, emit `agent-activated` per party, fan
   out, collect. Use a list-collecting `EventSink` in tests; assert event
   order: all `agent-activated` → N `response-item` → exactly one `done`.
4. **Wire verification** in `_resolve_items` (full items only; redacted/denied
   skip and stay `verified=False`). Add the bounded `Semaphore`. Test that a
   `verify -> False` flips a full item's badge but still emits the item.
5. **Implement `synthesis.synthesize`** + `llm.py` client. Real Claude call
   with the §3.1 prompt; add the empty-input guard. Snapshot-test that the
   prompt includes only verified-full answers and that redacted items appear
   as existence-only (no payload) — guards against leakage in the prompt.
6. **Assemble `FinalResponse` + emit `done`.** Build `provenance` from
   full+redacted contributors, set `item_count == len(items)`. Verify the
   `done` frame matches the contract example (including a 2-party fan-out →
   `item_count` reflecting emitted items, per the asker-exclusion rule).
7. **Integrate the real router/gate/verification** at checkpoint H8: delete
   the fakes, point imports at the real sibling modules, swap the keyword
   `search` stub for Hao's retrieval. No `run_query` call-site changes.
8. **Wire the API layer to `run_query`** (API subsystem): `POST /query` and
   the WS `{type:query}` frame construct an `Orchestrator(emit=ws_send)` and
   `await run_query(...)`; return `{query_id, from_agent, agents}` first, then
   let events stream. (The endpoint code is the API subsystem's; this step is
   the integration handshake.)
9. **Wire re-run** for `grant_access`: after the toggle, call
   `run_query(query, from_agent, query_id=original_id)` so a fresh
   `agent-activated → response-item → done` cycle streams on the same id.
10. **End-to-end demo-query test:** assert two parties return `full`/verified,
    one returns `redacted`, the synthesized answer cites both parties by name
    and mentions the restricted party as an access ask, and `done.provenance`
    lists the contributors.

---

## 6. Integration points with frozen contracts & other subsystems

- **`POST /query` (api-websocket.md):** API handler resolves `from_agent`
  (default demo asker if omitted), then invokes `run_query`. The immediate
  HTTP response `{query_id, from_agent, agents}` is built from the same
  `query_id` the orchestrator uses and the `list_party_agents(exclude=asker)`
  result — `agents` MUST equal the parties the orchestrator fans out to (the
  nodes that pulse). For an asker among the 3, that is a **2-party** fan-out
  (matches the contract example).
- **`agent-activated` event:** emitted by the orchestrator at fan-out, one per
  party, `status:"searching"`, before search/gate completes — re-emitted on a
  grant_access re-run. Payload exactly `{type, query_id, agent_id, party_name,
  status}`.
- **`response-item` event:** emitted from `_resolve_items`. Carries the five
  canonical data-model §4 fields plus `chunk_id` + `source_agent_id`.
  `verified` is `false` for `redacted`/`denied`. Items may arrive in any order
  across parties (the orchestrator gathers concurrently); the frontend keys by
  `source_agent_id`+`chunk_id`.
- **`done` event:** one per run. `synthesized_answer` from §3.1; `provenance`
  entries are `ResponseItem`-shaped (five fields + the two transport ids);
  `item_count == len(items)`.
- **`POST /grant_access` (api-websocket.md):** the gate/agents subsystem owns
  the visibility toggle and the `{chunk_id, new_visibility, query_id,
  rerunning}` response; the orchestrator owns the **re-run** it triggers. The
  API layer must store `query_id -> (query, from_agent)` to feed the re-run
  (noted under §2.2; lives in the API/router subsystem to avoid duplicate
  state).
- **`search()` (search-interface.md):** consumed *inside the router*, not the
  orchestrator. The orchestrator only ever sees `GatedItem`s, never raw
  `Chunk`s — so `embedding` and raw `restricted/private` `text` never reach
  it. Dennis's keyword stub and Hao's real cosine `search` are drop-in
  identical from the orchestrator's view.
- **Data model (data-model.md):** `ResponseItem` field names/shape mirror §4
  exactly; `GatedItem` is an internal pre-verification shape that does *not*
  cross the wire. Enums (`full|redacted|denied`, `public|restricted|private`)
  and the locked agent ids (`agent_northwind`, `agent_helios`, `agent_quanta`)
  come from `agents.py` / data-model §1.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| **Content leakage past the boundary** — the whole product thesis. If the orchestrator ever touched raw chunk `text`, restricted content could leak into synthesis/logs. | Orchestrator consumes only `GatedItem`s; gate + redaction run on the responder side of `router.dispatch`. `GatedItem` has no raw-`text` field. Synthesis prompt receives only verified-full `answer`s; redacted items pass as existence-only. Snapshot-test the synthesis prompt for absence of restricted payloads (build step 5). |
| **Isolation breach** — one party's index bleeding into another's results. | Fan-out calls `search` per-party with that party's `agent_id`; `search` guarantees `owner == agent_id`. Orchestrator never aggregates across indexes before the gate. `list_party_agents(exclude=asker)` ensures the asker never queries itself. |
| **Verification / synthesis latency** (spec §17) — three serial Claude calls per run would stall the demo. | Fan-out + verification run concurrently (`asyncio.gather`, bounded `Semaphore`). Tiny corpora + small `top_k` keep token counts low. Tight prompts. Verification is the designated downgrade to `claude-haiku-4-5` (single `llm.py` constant) if the loop is slow; synthesis stays opus. |
| **Claude call failure / timeout** mid-run blocks `done`. | `llm.complete` has a timeout + one retry. Verification fails **closed** (`verified=False`, never a false checkmark). Synthesis failure falls back to a deterministic "facts from [parties], synthesis unavailable" string so `done` always emits. |
| **A party errors during fan-out** (search raises, gate throws). | `gather(..., return_exceptions=True)` + `flatten_ok` drops/logs the failing party; the run still completes with the parties that succeeded. (Frontend renders a "no match" or omits the card.) |
| **`item_count` mismatch with emitted events** confusing the client. | `item_count = len(items)` computed from the exact list emitted; one source of truth in `_finish`. Tested in build step 6. |
| **Re-run state gap** — orchestrator is stateless, but `grant_access` needs the original query. | The `query_id -> (query, from_agent)` map lives in the API/router subsystem and is documented as a required integration point (§2.2, §6) rather than invented as a new contract shape. |
| **Contract gap: no per-run error event.** The WS contract defines only `agent-activated`/`response-item`/`done`; there is no `error` frame. If a whole run fails, the client has nothing to render. | Out of scope to invent a new event (contracts are frozen). Mitigation within contract: always emit a `done` (possibly with the fallback synthesized answer + empty/partial provenance) so the client is never left hanging. Flag for a 2-minute sync if a real error channel is needed post-MVP. |
| **Ordering regression** — gate accidentally running before retrieve, or in the orchestrator. | Enforcement boundary is structural: `search` is gate-free (search-interface.md), the gate is only reachable via `router.dispatch` on the responder side, and the orchestrator imports neither `gate` nor `search` for content. Architectural test: assert `orchestrator.py` does not import `search`/`gate` for chunk text. |
