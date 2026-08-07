"""OpenRouter API clients for the three model roles.

This module talks to models. It does not control the desktop and does not parse
coordinates (see ``agent.grounding``) or own prompt text (see ``agent.prompts``).

Public entry points
-------------------
get_client()
    Shared OpenRouter SDK client (lazy singleton).
vision_observe(image_path, objective, history=None)
    Screenshot → structured observation / next-step prose.
action_decide(vision_text, tools)
    Vision prose + tool schemas → ``[{name, parameters}, ...]``.
ground_click(query, image_path)
    Screenshot + click query → clamped ``(x, y)`` pixels.

Model IDs (env, with defaults)
------------------------------
VISION_MODEL / ACTION_MODEL / GROUNDING_MODEL — see ``.env.example``.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from openrouter import OpenRouter
from PIL import Image

from agent import prompts
from agent.grounding import clamp_coordinates, extract_coordinates

DEFAULT_VISION_MODEL = "qwen/qwen2.5-vl-72b-instruct"
DEFAULT_ACTION_MODEL = "openai/gpt-4o-mini"
DEFAULT_GROUNDING_MODEL = "qwen/qwen2.5-vl-72b-instruct"

_client: OpenRouter | None = None


def get_client() -> OpenRouter:
    """Return a process-wide OpenRouter client, creating it on first use.

    Requires ``OPENROUTER_API_KEY`` in the environment.

    Raises:
        RuntimeError: If the API key is missing.
    """
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        _client = OpenRouter(
            api_key=api_key,
            x_open_router_title="computer-use-agent",
        )
    return _client


def _model(env_name: str, default: str) -> str:
    """Read a model id from env, falling back to ``default`` if unset/blank."""
    return os.getenv(env_name, default).strip() or default


def vision_model() -> str:
    """OpenRouter model id used for screenshot understanding."""
    return _model("VISION_MODEL", DEFAULT_VISION_MODEL)


def action_model() -> str:
    """OpenRouter model id used for tool selection."""
    return _model("ACTION_MODEL", DEFAULT_ACTION_MODEL)


def grounding_model() -> str:
    """OpenRouter model id used for click localization."""
    return _model("GROUNDING_MODEL", DEFAULT_GROUNDING_MODEL)


def _image_data_url(image_path: str | Path) -> str:
    """Encode a local image file as a ``data:<mime>;base64,...`` URL."""
    path = Path(image_path)
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _image_content_parts(image_path: str | Path, text: str) -> list[dict[str, Any]]:
    """Build multimodal user content: text part + image part."""
    return [
        {"type": "text", "text": text},
        {
            "type": "image_url",
            "image_url": {"url": _image_data_url(image_path)},
        },
    ]


def _message_text(content: Any) -> str:
    """Normalize assistant ``content`` (str, list of parts, or None) to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        return "\n".join(p for p in parts if p)
    return str(content)


def _tools_to_openrouter(tools: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert simple tool specs into OpenRouter function-tool definitions.

    Expected input shape (same idea as upstream open-computer-use)::

        {
            "click": {
                "description": "Click on a UI element.",
                "params": {"query": "Element to click"},
            },
            "stop": {"description": "Task is done.", "params": {}},
        }
    """
    converted: list[dict[str, Any]] = []
    for name, spec in tools.items():
        params = spec.get("params") or {}
        properties = {
            key: {"type": "string", "description": str(desc)}
            for key, desc in params.items()
        }
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": spec.get("description") or name,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties.keys()),
                    },
                },
            }
        )
    return converted


def vision_observe(
    image_path: str | Path,
    objective: str,
    history: str | None = None,
) -> str:
    """Ask the vision model what is on screen and what to do next.

    Args:
        image_path: Path to a PNG (or other) desktop screenshot.
        objective: User goal for this run.
        history: Optional prior thoughts/actions for context.

    Returns:
        Structured prose (objective / see / complete? / next step).
    """
    user_text = prompts.build_vision_user_message(objective, history)
    client = get_client()
    result = client.chat.send(
        model=vision_model(),
        messages=[
            {
                "role": "user",
                "content": _image_content_parts(image_path, user_text),
            }
        ],
        stream=False,
    )
    return _message_text(result.choices[0].message.content).strip()


def action_decide(
    vision_text: str,
    tools: dict[str, Any],
) -> list[dict[str, Any]]:
    """Ask the action model to pick one tool call from vision prose.

    Args:
        vision_text: Output of ``vision_observe``.
        tools: Simple tool registry ``{name: {description, params}}``.

    Returns:
        Normalized calls like ``[{"name": "click", "parameters": {...}}]``.
        Empty list if the model returned no tool calls.
    """
    client = get_client()
    result = client.chat.send(
        model=action_model(),
        messages=[
            {"role": "system", "content": prompts.ACTION_SYSTEM},
            {
                "role": "user",
                "content": prompts.build_action_user_message(vision_text),
            },
        ],
        tools=_tools_to_openrouter(tools),
        tool_choice="auto",
        parallel_tool_calls=False,
        stream=False,
    )
    message = result.choices[0].message
    calls = message.tool_calls or []
    normalized: list[dict[str, Any]] = []
    for call in calls:
        name = call.function.name
        raw_args = call.function.arguments or "{}"
        try:
            parameters = json.loads(raw_args)
        except json.JSONDecodeError:
            parameters = {"_raw": raw_args}
        if not isinstance(parameters, dict):
            parameters = {"value": parameters}
        normalized.append({"name": name, "parameters": parameters})
    return normalized


def ground_click(query: str, image_path: str | Path) -> tuple[int, int]:
    """Ask the grounding model where to click, then parse and clamp pixels.

    Args:
        query: Natural-language description of the UI target (e.g. "Chrome icon").
        image_path: Screenshot to search within.

    Returns:
        ``(x, y)`` in image pixel space, clamped to the image bounds.

    Raises:
        ValueError: If the model reply cannot be parsed into coordinates.
    """
    path = Path(image_path)
    with Image.open(path) as image:
        width, height = image.size

    user_text = prompts.build_grounding_user_message(query, width, height)
    client = get_client()
    result = client.chat.send(
        model=grounding_model(),
        messages=[
            {
                "role": "user",
                "content": _image_content_parts(path, user_text),
            }
        ],
        stream=False,
    )
    text = _message_text(result.choices[0].message.content)
    coords = extract_coordinates(text)
    if coords is None:
        raise ValueError(f"Could not parse coordinates from grounding reply: {text!r}")
    return clamp_coordinates(coords, (width, height))
