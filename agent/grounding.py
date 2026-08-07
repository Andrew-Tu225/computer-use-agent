"""Coordinate parsing and debug overlays for click grounding.

``agent.models.ground_click`` returns raw model text that must be turned into
pixels. This module owns that post-processing — it does not call any LLM.

Typical flow
------------
1. ``extract_coordinates(text)`` — parse ``x,y`` or a bbox midpoint.
2. ``clamp_coordinates(coords, image.size)`` — keep clicks inside the image.
3. ``draw_big_dot`` / ``annotate_and_save`` — red-dot PNG for eyeballing accuracy.

Sandbox screenshots are usually 1024×720 (see ``desktop.create_sandbox``).
Always clamp using the *actual* image size; resolution mismatch is a common bug.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

# Default desktop resolution used when creating the E2B sandbox.
DEFAULT_SCREEN_SIZE = (1024, 720)


def extract_coordinates(text: str) -> tuple[int, int] | None:
    """Parse ``(x, y)`` from free-form grounding model output.

    Accepts a point (two numbers) or a box (four+ numbers → midpoint).
    Also recognizes upstream-style ``<|box_start|>...<|box_end|>`` wrappers.

    Args:
        text: Raw model reply that should contain coordinates.

    Returns:
        Integer pixel pair, or ``None`` if fewer than two numbers are found.
    """
    if not text:
        return None

    match = re.search(r"<\|box_start\|>(.*?)<\|box_end\|>", text, re.DOTALL)
    inner = match.group(1) if match else text

    numbers = [float(num) for num in re.findall(r"\d+\.\d+|\d+", inner)]
    if len(numbers) == 2:
        return int(numbers[0]), int(numbers[1])
    if len(numbers) >= 4:
        x = int((numbers[0] + numbers[2]) / 2)
        y = int((numbers[1] + numbers[3]) / 2)
        return x, y
    return None


def clamp_coordinates(
    coords: tuple[int, int],
    size: tuple[int, int],
) -> tuple[int, int]:
    """Force ``(x, y)`` into ``[0, width)`` × ``[0, height)``.

    Args:
        coords: Proposed click point.
        size: Image ``(width, height)`` in pixels.

    Returns:
        Clamped integer coordinates safe to pass to ``left_click``.
    """
    x, y = coords
    width, height = size
    return (
        max(0, min(x, max(width - 1, 0))),
        max(0, min(y, max(height - 1, 0))),
    )


def draw_big_dot(
    image: Image.Image,
    coordinates: tuple[int, int],
    color: str = "red",
    radius: int = 12,
) -> Image.Image:
    """Return a copy of ``image`` with a filled circle at ``coordinates``.

    Used so humans can quickly judge whether grounding landed on the right UI.
    """
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    x, y = coordinates
    bounding_box = [x - radius, y - radius, x + radius, y + radius]
    draw.ellipse(bounding_box, fill=color, outline=color)
    return annotated


def annotate_and_save(
    image_path: str | Path,
    coords: tuple[int, int],
    output_path: str | Path,
    *,
    color: str = "red",
    radius: int = 12,
) -> Path:
    """Clamp coords, draw a debug dot on the screenshot, and write a PNG.

    Args:
        image_path: Source screenshot.
        coords: Proposed click point (will be clamped to image bounds).
        output_path: Where to write the annotated PNG.
        color: Dot fill/outline color.
        radius: Dot radius in pixels.

    Returns:
        Path to the written annotated image.
    """
    path = Path(image_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(path) as image:
        clamped = clamp_coordinates(coords, image.size)
        annotated = draw_big_dot(image, clamped, color=color, radius=radius)
        annotated.save(out)

    return out
