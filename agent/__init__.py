"""Agent package: model clients, prompts, and grounding helpers.

Modules
-------
models
    OpenRouter calls for vision, action, and grounding.
prompts
    Prompt text and ``build_*`` helpers used by ``models``.
grounding
    Coordinate parsing and red-dot debug overlays (no LLM calls).

The agent loop and tool execution live elsewhere (not in this package yet).
"""
