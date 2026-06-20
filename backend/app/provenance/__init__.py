"""Provenance assembly subsystem — wedge piece 2 (provenance-verification.md).

Re-exports: assemble_provenance, build_response_item. Owns the provenance pointer
assembly (pointer.py) and the build_response_item branch that invokes verification
ONLY for `full` items (assembler.py). The verification Claude call itself lives in
app/claude/verification.py (BUILD_INDEX.md §2.1).
"""
from __future__ import annotations

from app.provenance.pointer import assemble_provenance  # noqa: F401
from app.provenance.assembler import build_response_item  # noqa: F401

__all__ = ["assemble_provenance", "build_response_item"]
