"""Tool registry: schemas for the action model + handlers that drive the desktop.

Add a new tool by appending an entry to ``TOOLS`` with description, params, and
handler. The loop never hard-codes tool names beyond stop semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.grounding import annotate_and_save
from agent.models import ground_click
from desktop import sandbox as desktop


@dataclass
class RunContext:
    """Per-run state shared by tool handlers (output paths, counters)."""

    output_dir: Path
    step: int = 0
    image_counter: int = 0
    last_screenshot: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def next_image_prefix(self, kind: str) -> str:
        self.image_counter += 1
        return f"{kind}_{self.image_counter:03d}"


ToolHandler = Callable[..., str]


def _click(*, query: str, ctx: RunContext) -> str:
    """Ground ``query`` on a fresh screenshot, save a red-dot debug image, click."""
    shot = desktop.screenshot(
        output_dir=ctx.output_dir,
        prefix=ctx.next_image_prefix("screenshot"),
    )
    ctx.last_screenshot = shot
    try:
        x, y = ground_click(query, shot)
    except Exception as exc:
        return f"Grounding failed for {query!r}: {exc}"

    dot_path = annotate_and_save(
        shot,
        (x, y),
        ctx.output_dir / f"{ctx.next_image_prefix('location')}.png",
    )
    desktop.left_click(x, y)
    desktop.wait(800)
    return f"Clicked {query!r} at ({x}, {y}); debug dot at {dot_path.name}"


def _type_text(*, text: str, ctx: RunContext) -> str:
    desktop.write(text)
    return "The text has been typed."


def _press_key(*, name: str, ctx: RunContext) -> str:
    # E2B accepts names like "enter" or combinations as lists; pass strings through.
    desktop.press(name)
    return f"The key {name!r} has been pressed."


def _run_command(*, command: str, ctx: RunContext) -> str:
    return desktop.run(command)


def _stop(*, ctx: RunContext) -> str:
    return "Stopped."


# Registry shape used by action_decide (description/params) and execute (handler).
TOOLS: dict[str, dict[str, Any]] = {
    "click": {
        "description": "Click on a specified UI element by describing it.",
        "params": {"query": "Item or UI element on the screen to click"},
        "handler": _click,
    },
    "type_text": {
        "description": "Type a specified text into the focused field.",
        "params": {"text": "Text to type"},
        "handler": _type_text,
    },
    "press_key": {
        "description": "Send a key or key name to the system (e.g. enter, tab).",
        "params": {"name": "Key name (e.g. 'enter', 'tab', 'escape')"},
        "handler": _press_key,
    },
    "run_command": {
        "description": "Run a shell command in the sandbox and return the output.",
        "params": {"command": "Shell command to run synchronously"},
        "handler": _run_command,
    },
    "stop": {
        "description": "Indicate that the task has been completed.",
        "params": {},
        "handler": _stop,
    },
}


def schemas_for_action(
    tools: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Strip handlers; return ``{name: {description, params}}`` for ``action_decide``."""
    source = tools if tools is not None else TOOLS
    return {
        name: {
            "description": spec["description"],
            "params": spec.get("params") or {},
        }
        for name, spec in source.items()
    }


def execute(
    name: str,
    parameters: dict[str, Any] | None,
    ctx: RunContext,
    tools: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Run a tool by name with the given parameters and run context.

    Returns:
        Observation string for the agent history / log.
    """
    source = tools if tools is not None else TOOLS
    spec = source.get(name)
    if spec is None:
        return f"Unknown tool: {name!r}"

    handler: ToolHandler = spec["handler"]
    params = dict(parameters or {})
    try:
        return handler(ctx=ctx, **params)
    except TypeError as exc:
        return f"Bad arguments for {name}: {exc}"
    except Exception as exc:
        return f"Error executing {name}: {exc}"
