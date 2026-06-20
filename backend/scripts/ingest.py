"""Offline ingestion: real exported Claude data -> a party's seed corpus.

Reads ONE party's raw data (Claude Code JSONL transcripts + Claude.ai website
conversations.json) under data/raw/<party>/, extracts question+resolution units,
filters noise, dedupes, ranks by engineering relevance, caps to --max-chunks, and
writes app/data/corpora/<agent_id>.json in the exact Chunk shape (data-model.md §2)
with `visibility` defaulted to "public" for hand-tiering afterward.

NOT imported by the app — pure stdlib offline tooling. Run once per party:

    python scripts/ingest.py --party dennis --agent-id agent_northwind
    python scripts/ingest.py --party hao    --agent-id agent_helios
    python scripts/ingest.py --party other  --agent-id agent_quanta --website-only

The emitted JSON is the editable artifact: a human then sets individual rows to
"restricted"/"private" (see scripts/tier.py).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from dataclasses import dataclass

# ---- paths -----------------------------------------------------------------
DEFAULT_RAW_ROOT = pathlib.Path("/home/dennis/Projects/beacon/data/raw")
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "data" / "corpora"

# ---- tuning knobs ----------------------------------------------------------
MIN_ANSWER_CHARS = 80      # drop "ok"/"done"/trivial answers
MIN_QUESTION_CHARS = 12    # drop bare tokens
MAX_CHARS = 4000           # drop pasted logs / huge tool dumps on either side
DOC_TITLE_WORDS = 8

# Engineering-relevance keywords used to rank surviving Q&A units (higher = kept).
ENG_KEYWORDS = (
    "how", "why", "fix", "error", "bug", "debug", "implement", "build", "deploy",
    "test", "fail", "crash", "optimize", "refactor", "design", "config", "install",
    "api", "function", "class", "database", "query", "server", "client", "async",
    "type", "import", "exception", "performance", "race", "memory", "thread",
)

# Claude Code / harness artifacts that leak in as fake "user" turns — drop the unit.
ARTIFACT_MARKERS = (
    "<task-notification>", "<system-reminder>", "<task-id>", "<command-name>",
    "<command-message>", "<command-args>", "<local-command-stdout>",
    "execute this task immediately", "write files", "caveat: the messages below",
    "this session is being continued", "<persisted-output>", "tool_use_error",
)

# Secret-shaped strings — drop the whole unit so nothing sensitive enters a corpus.
SECRET_RE = re.compile(
    r"sk-ant-[a-z0-9-]{8,}|sk-[a-zA-Z0-9]{20,}|ghp_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|Bearer\s+[A-Za-z0-9._-]{20,}"
    r"|token saved to|xox[baprs]-[A-Za-z0-9-]{10,}|password\s*[:=]\s*\S+",
    re.IGNORECASE,
)


@dataclass
class QAUnit:
    question: str
    answer: str
    doc_title: str
    source_id: str          # session uuid / conversation uuid -> parent_doc grouping
    source_kind: str        # "claude-code" | "website"


# ---- shared text helpers ---------------------------------------------------
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _derive_title(question: str) -> str:
    words = _norm(question).split()
    title = " ".join(words[:DOC_TITLE_WORDS])
    return (title[:60] + "...") if len(title) > 60 else title or "Untitled"


def _content_to_text(content) -> tuple[str, bool]:
    """Return (joined text-block text, has_tool_block). Strings pass through;
    block arrays keep only `type:"text"` blocks and flag any tool_use/tool_result."""
    if isinstance(content, str):
        return content, False
    if isinstance(content, list):
        parts, has_tool = [], False
        for b in content:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                parts.append(b.get("text", ""))
            elif t in ("tool_use", "tool_result"):
                has_tool = True
            # "thinking" and other block types are dropped
        return "\n".join(parts), has_tool
    return "", False


# ---- format readers --------------------------------------------------------
def read_claude_code_session(path: pathlib.Path) -> list[QAUnit]:
    """Parse one .jsonl session. A QA unit = a REAL user turn (content is a str or
    all-text blocks, never tool_use/tool_result) followed by the next assistant turn."""
    units: list[QAUnit] = []
    session_id = path.stem
    pending_q: str | None = None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return units
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        kind = obj.get("type")
        if kind not in ("user", "assistant"):
            continue
        msg = obj.get("message") or {}
        text, has_tool = _content_to_text(msg.get("content"))
        text = _norm(text)
        if kind == "user":
            # A real human turn carries plain text and no tool echoes.
            if text and not has_tool:
                pending_q = text
        elif kind == "assistant" and text and pending_q:
            units.append(QAUnit(pending_q, text, _derive_title(pending_q),
                                session_id, "claude-code"))
            pending_q = None
    return units


def read_website_conversations(path: pathlib.Path) -> list[QAUnit]:
    """Parse conversations.json (array of conversations). A QA unit = a human message
    followed by the next assistant message. text = msg.text or joined content text."""
    units: list[QAUnit] = []
    try:
        convs = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return units
    if not isinstance(convs, list):
        return units
    for conv in convs:
        if not isinstance(conv, dict):
            continue
        title = _norm(conv.get("name") or conv.get("summary") or "")
        source_id = conv.get("uuid", "")
        pending_q: str | None = None
        for msg in conv.get("chat_messages", []):
            if not isinstance(msg, dict):
                continue
            text = _norm(msg.get("text") or _content_to_text(msg.get("content"))[0])
            sender = msg.get("sender")
            if sender == "human":
                if text:
                    pending_q = text
            elif sender == "assistant" and text and pending_q:
                units.append(QAUnit(pending_q, text,
                                    title or _derive_title(pending_q),
                                    source_id, "website"))
                pending_q = None
    return units


# ---- filter / dedupe / rank ------------------------------------------------
def is_noise(u: QAUnit) -> bool:
    q, a = u.question, u.answer
    if len(q) < MIN_QUESTION_CHARS or len(a) < MIN_ANSWER_CHARS:
        return True
    if len(q) > MAX_CHARS or len(a) > MAX_CHARS:
        return True
    if q.startswith("/") or len(q.split()) < 2:   # slash-command / single token
        return True
    if q.lstrip().startswith("<"):                # system/XML tag, not a human turn
        return True
    combined = f"{q}\n{a}".lower()
    if any(m in combined for m in ARTIFACT_MARKERS):   # harness spam
        return True
    if SECRET_RE.search(f"{q}\n{a}"):                  # secret-shaped -> never include
        return True
    return False


def _relevance(u: QAUnit) -> float:
    ql = u.question.lower()
    kw = sum(1 for k in ENG_KEYWORDS if k in ql)
    # Prefer self-contained answers (200-1500 chars); penalize extremes.
    la = len(u.answer)
    length_score = 1.0 if 200 <= la <= 1500 else 0.3
    return kw + length_score


def select_chunks(units: list[QAUnit], max_chunks: int) -> list[QAUnit]:
    clean = [u for u in units if not is_noise(u)]
    # Dedupe by normalized-question (collapses re-asks) and by 40-char prefix;
    # cap repeats of any single doc_title so one topic can't flood the corpus.
    seen_q, seen_prefix, title_count, deduped = set(), set(), {}, []
    MAX_PER_TITLE = 2
    for u in clean:
        key = u.question.lower()
        prefix = key[:40]
        tkey = u.doc_title.lower()
        if key in seen_q or prefix in seen_prefix:
            continue
        if title_count.get(tkey, 0) >= MAX_PER_TITLE:
            continue
        seen_q.add(key)
        seen_prefix.add(prefix)
        title_count[tkey] = title_count.get(tkey, 0) + 1
        deduped.append(u)
    # Rank by relevance desc; stable so identical raw data -> identical corpus.
    deduped.sort(key=_relevance, reverse=True)
    selected = deduped[:max_chunks]
    # Re-sort the kept set by question text for a stable, diff-friendly file order.
    selected.sort(key=lambda u: u.question.lower())
    return selected


# ---- emit ------------------------------------------------------------------
def to_chunk(u: QAUnit, agent_id: str, doc_idx: int, chunk_idx: int) -> dict:
    slug = agent_id.removeprefix("agent_")
    return {
        "chunk_id": f"{slug}_c{chunk_idx:03d}",
        "parent_doc_id": f"{slug}_d{doc_idx:02d}",
        "doc_title": u.doc_title,
        "owner": agent_id,
        "visibility": "public",                 # DEFAULT — hand-tier afterward
        "text": f"Q: {u.question}\n\nA: {u.answer}",
    }


def iter_cc_sessions(party_root: pathlib.Path):
    """All *.jsonl transcripts anywhere under the party root (handles both the
    dennis/claude-code/ and hao/claude-code-sessions/projects/ nestings); skips
    *.wakatime sidecars and the website/ dir (which holds .json, not .jsonl)."""
    for p in sorted(party_root.rglob("*.jsonl")):
        if p.name.endswith(".wakatime"):
            continue
        yield p


def ingest_party(party: str, agent_id: str, max_chunks: int,
                 raw_root: pathlib.Path, website_only: bool) -> pathlib.Path:
    party_root = raw_root / party
    units: list[QAUnit] = []

    if not website_only:
        for session in iter_cc_sessions(party_root):
            units.extend(read_claude_code_session(session))

    website = party_root / "website" / "conversations.json"
    if website.exists():
        units.extend(read_website_conversations(website))

    selected = select_chunks(units, max_chunks)

    # Assign one parent_doc per distinct source, chunk_id sequential.
    doc_index: dict[str, int] = {}
    chunks = []
    for i, u in enumerate(selected):
        if u.source_id not in doc_index:
            doc_index[u.source_id] = len(doc_index)
        chunks.append(to_chunk(u, agent_id, doc_index[u.source_id], i))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{agent_id}.json"
    payload = {
        "_comment": (
            f"Ingested from real {party} data ({len(units)} raw Q&A units -> "
            f"{len(chunks)} chunks). visibility defaults to 'public'; hand-tier with "
            f"scripts/tier.py. embedding backfilled by scripts/build_embeddings.py."
        ),
        "chunks": chunks,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"[ingest] {party} -> {agent_id}: {len(units)} raw units, "
          f"{len(chunks)} chunks -> {out_path}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest a party's raw Claude data into a seed corpus.")
    ap.add_argument("--party", required=True, help="raw data folder under data/raw/ (e.g. dennis)")
    ap.add_argument("--agent-id", required=True, help="target agent id (e.g. agent_northwind)")
    ap.add_argument("--max-chunks", type=int, default=25, help="cap on kept chunks (default 25)")
    ap.add_argument("--website-only", action="store_true", help="skip Claude Code transcripts")
    ap.add_argument("--raw-root", type=pathlib.Path, default=DEFAULT_RAW_ROOT)
    args = ap.parse_args()
    ingest_party(args.party, args.agent_id, args.max_chunks, args.raw_root, args.website_only)


if __name__ == "__main__":
    main()
