"""Agent package: model clients, prompts, grounding, tools, and loop.

Modules
-------
models
    OpenRouter calls for vision, action, and grounding.
prompts
    Prompt text and ``build_*`` helpers used by ``models``.
grounding
    Coordinate parsing and red-dot debug overlays (no LLM calls).
tools
    Tool schemas + desktop handlers (``click``, ``type_text``, …).
loop
    See → decide → act → observe orchestration and ``run_log.md``.
agent
    Thin ``ComputerAgent`` facade with ``run(objective)``.
"""
