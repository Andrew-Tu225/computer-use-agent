"""Prompt templates and builders for the three model roles.

Edit this file when changing how models are instructed. Each section owns one
role in the see → decide → ground pipeline:

  Vision    — screenshot → structured observation + next step (prose)
  Action    — vision prose → one tool call (schemas come from the API)
  Grounding — screenshot + query → pixel coordinates

Call the ``build_*`` helpers from ``agent.models``; keep raw string constants
here so prompts stay easy to read and tweak.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Vision — perceive the screen and propose a single next step
# ---------------------------------------------------------------------------
# Intent matches open-computer-use's append_screenshot observation format:
# restate objective → list relevant UI → complete? → one next step if not.

VISION_RESPONSE_FORMAT = """\
The objective is: [restate the objective]
On the screen, I see: [extensive list of windows, icons, menus, apps, and UI \
elements relevant to the objective]
This means the objective is: [complete|not complete]

(Only continue if the objective is not complete.)
The next step is to [click|type|run the shell command] [single concrete step] \
in order to [what you expect to happen]."""

VISION_INTRO = (
    "This image shows the current display of the computer. "
    "Describe only what you can see, then decide the next single step."
)


def build_vision_user_message(objective: str, history: str | None = None) -> str:
    """Build the vision-model user message for a screenshot turn.

    Args:
        objective: What the agent is trying to accomplish.
        history: Optional recent thoughts/actions for context.

    Returns:
        Full user-message text (image is attached separately by models.py).
    """
    parts = [
        VISION_INTRO,
        f"The user's objective is: {objective}",
    ]
    if history and history.strip():
        parts.append(f"Recent history:\n{history.strip()}")
    parts.append("Respond in exactly this format:")
    parts.append(VISION_RESPONSE_FORMAT)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Action — turn vision prose into exactly one tool call
# ---------------------------------------------------------------------------
# Tool names and parameter schemas are passed via the OpenRouter tools API,
# not pasted into this prompt.

ACTION_SYSTEM = """\
You are an AI assistant that controls a remote computer through tools.

Rules:
- Choose exactly one tool call that matches the next step in the thought.
- If the objective is already complete, call stop.
- Do not invent tools that are not provided.
- Prefer click with a clear UI-element query when the next step is a GUI click."""

ACTION_USER_PREFIX = "Thought from the vision model:"


def build_action_user_message(vision_text: str) -> str:
    """Build the action-model user message from vision output.

    Args:
        vision_text: Structured prose returned by ``vision_observe``.

    Returns:
        User-message text asking for a single tool call (or stop).
    """
    return (
        f"{ACTION_USER_PREFIX}\n"
        f"{vision_text.strip()}\n\n"
        "Call exactly one tool to take this next step, "
        "or call stop if the objective is complete."
    )


# ---------------------------------------------------------------------------
# Grounding — map a natural-language UI query to pixel coordinates
# ---------------------------------------------------------------------------
# Reply must stay parseable by agent.grounding.extract_coordinates.

GROUNDING_INTRO = (
    "You locate UI elements on a desktop screenshot and return click coordinates."
)

GROUNDING_REPLY_RULES = """\
Reply with ONLY coordinates in one of these forms (no other text):
- x,y
- (x, y)
- four numbers for a box: left top right bottom  (midpoint will be used)"""


def build_grounding_user_message(query: str, width: int, height: int) -> str:
    """Build the grounding-model user message for a click query.

    Args:
        query: Natural-language description of the UI element to click.
        width: Screenshot width in pixels.
        height: Screenshot height in pixels.

    Returns:
        User-message text (image is attached separately by models.py).
    """
    return "\n\n".join(
        [
            GROUNDING_INTRO,
            f"Screenshot size: {width}x{height} pixels.",
            f"Find this UI element and return its click point:\n{query.strip()}",
            GROUNDING_REPLY_RULES,
        ]
    )
