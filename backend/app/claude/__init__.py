"""Claude (Anthropic API) calls: one shared client + the three passes.

See backend/docs/redaction.md and backend/docs/provenance-verification.md. Holds the
shared AsyncAnthropic client + model constants (client.py), the frozen prompts
(prompts.py), and the redaction / verification / synthesis calls. NOT embeddings —
Anthropic has no embeddings endpoint (those live in app/agents/embeddings.py).
"""
