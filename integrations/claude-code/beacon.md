---
description: Ask the Beacon permissioned knowledge network (the /beacon flag, in the terminal)
argument-hint: <question>
allowed-tools: Bash(python /home/dennis/Projects/beacon/backend/scripts/beacon_ask.py:*)
---

!`python /home/dennis/Projects/beacon/backend/scripts/beacon_ask.py "$ARGUMENTS"`

Reply in two parts:

1. **The cold Beacon output, verbatim.** Ignore any leading `> **Presentation …**` blockquote
   line (that's an instruction meant for other assistants, not for you). Then reproduce the rest
   of the block above exactly as printed — the synthesized answer, the **Sources** list, and the
   **Per-party results** — with no changes, no trimming, no summarizing. Always show the Sources
   and Per-party gating in full; they are the point.

2. A `---` divider, then a short section headed **My read:** — your own take on what came back:
   what's notable or trustworthy, caveats or gaps, what the per-party gating implies, or a tighter
   follow-up query worth running. Keep it brief (2–5 sentences). This is additive — it never
   replaces or condenses the verbatim block above it.

(If the output is a connection error instead, skip both parts and reply with just that error plus
one line: "The Beacon stack isn't running — start it with `cd backend && ./scripts/run.sh`.")
