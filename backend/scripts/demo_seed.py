"""Plant the locked demo scenario into the corpora on disk + rebuild embeddings (idempotent).

Run once before the demo, and to reset DISK state between sessions:

    cd backend && python -m scripts.demo_seed

Removes any prior demo chunks (by id), re-adds the fresh planted set with their tiers, and
re-embeds so the planted chunks have vectors in embeddings.npz. The faster between-takes
reset (no restart, re-arms the granted chunk in the LIVE index) is POST /demo/reset.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.agents.corpus import CORPORA_DIR
from app.demo import DEMO_CHUNKS


def plant() -> None:
    demo_ids = {c["chunk_id"] for c in DEMO_CHUNKS}
    by_agent: dict[str, list[dict]] = {}
    for c in DEMO_CHUNKS:
        by_agent.setdefault(c["owner"], []).append(c)

    for agent_id, planted in by_agent.items():
        path = CORPORA_DIR / f"{agent_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        kept = [c for c in data.get("chunks", []) if c["chunk_id"] not in demo_ids]  # drop old demo
        data["chunks"] = kept + planted                                              # add fresh demo
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tiers = ", ".join(f"{c['chunk_id']}={c['visibility']}" for c in planted)
        print(f"[demo_seed] {agent_id}: {len(planted)} demo chunks ({len(data['chunks'])} total) — {tiers}")

    from scripts.build_embeddings import build_embeddings
    build_embeddings()   # re-embed so planted chunks have vectors in the npz cache
    print("[demo_seed] done — corpora planted + embedded. Demo query:")
    from app.demo import DEMO_QUERY
    print(f"           {DEMO_QUERY!r}")


if __name__ == "__main__":
    plant()
