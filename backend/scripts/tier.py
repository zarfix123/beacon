"""Flip one chunk's visibility tier in a seed corpus, safely.

Avoids hand-editing JSON (and breaking its syntax mid-demo-prep). Loads the corpus,
mutates exactly one chunk's `visibility`, rewrites the file with stable formatting.

    python scripts/tier.py agent_northwind northwind_c014 restricted
    python scripts/tier.py agent_quanta    quanta_c007    private

List a corpus's chunks (id + current tier + title) with --list:

    python scripts/tier.py agent_northwind --list
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

CORPORA_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "data" / "corpora"
VALID = ("public", "restricted", "private")


def _load(agent_id: str) -> tuple[pathlib.Path, dict]:
    path = CORPORA_DIR / f"{agent_id}.json"
    if not path.exists():
        sys.exit(f"[tier] no corpus at {path} — run scripts/ingest.py first")
    return path, json.loads(path.read_text(encoding="utf-8"))


def list_chunks(agent_id: str) -> None:
    _, data = _load(agent_id)
    for c in data.get("chunks", []):
        print(f"  {c['chunk_id']:>16}  {c['visibility']:<10}  {c['doc_title']}")


def set_tier(agent_id: str, chunk_id: str, visibility: str) -> None:
    if visibility not in VALID:
        sys.exit(f"[tier] visibility must be one of {VALID}")
    path, data = _load(agent_id)
    for c in data.get("chunks", []):
        if c["chunk_id"] == chunk_id:
            old = c["visibility"]
            c["visibility"] = visibility
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            print(f"[tier] {agent_id}/{chunk_id}: {old} -> {visibility}")
            return
    sys.exit(f"[tier] chunk_id {chunk_id} not found in {agent_id}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Set a chunk's visibility tier.")
    ap.add_argument("agent_id")
    ap.add_argument("chunk_id", nargs="?", help="omit with --list")
    ap.add_argument("visibility", nargs="?", choices=VALID)
    ap.add_argument("--list", action="store_true", help="list chunk ids + tiers + titles")
    args = ap.parse_args()
    if args.list:
        list_chunks(args.agent_id)
    elif args.chunk_id and args.visibility:
        set_tier(args.agent_id, args.chunk_id, args.visibility)
    else:
        ap.error("provide <chunk_id> <visibility>, or --list")


if __name__ == "__main__":
    main()
