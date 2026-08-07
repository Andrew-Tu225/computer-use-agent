"""Manual isolation checks for vision / action / grounding (no agent loop).

Runs each client once against a fixture screenshot and prints results. Saves a
red-dot grounding image under ``output/check_models/``.

Usage
-----
::

    poetry run python scripts/check_models.py
    poetry run python scripts/check_models.py --image path/to/screenshot.png
    poetry run python scripts/check_models.py --query "Chrome icon"

Needs ``OPENROUTER_API_KEY``. If ``--image`` is omitted, uses the first PNG
found under ``output/demo_desktop/`` (create one with
``poetry run python main.py --demo-desktop``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.grounding import annotate_and_save
from agent.models import action_decide, ground_click, vision_observe

DEFAULT_OBJECTIVE = "Open the Chrome browser by clicking its icon"
DEFAULT_QUERY = "Chrome icon"
DEMO_DIRS = (
    ROOT / "output" / "demo_desktop",
    ROOT / "output",
)
OUT_DIR = ROOT / "output" / "check_models"

# Minimal tool surface for exercising action_decide in isolation.
SAMPLE_TOOLS = {
    "click": {
        "description": "Click on a specified UI element.",
        "params": {"query": "Item or UI element on the screen to click"},
    },
    "type_text": {
        "description": "Type a specified text into the system.",
        "params": {"text": "Text to type"},
    },
    "stop": {
        "description": "Indicate that the task has been completed.",
        "params": {},
    },
}


def find_fixture_image(explicit: str | None) -> Path:
    """Resolve the screenshot path from ``--image`` or demo output folders.

    Args:
        explicit: Optional path from the CLI.

    Returns:
        Path to an existing PNG.

    Raises:
        SystemExit: If the path is missing or no demo PNGs exist.
    """
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f"Image not found: {path}")
        return path

    candidates: list[Path] = []
    for folder in DEMO_DIRS:
        if folder.is_dir():
            candidates.extend(sorted(folder.glob("*.png")))
    if not candidates:
        raise SystemExit(
            "No PNG fixture found. Run `poetry run python main.py --demo-desktop` "
            "first, or pass --image path/to/screenshot.png"
        )
    return candidates[0]


def main() -> None:
    """Run vision → action → grounding against one screenshot and print results."""
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Path to a desktop screenshot PNG")
    parser.add_argument("--objective", default=DEFAULT_OBJECTIVE)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    args = parser.parse_args()

    image_path = find_fixture_image(args.image)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Using fixture: {image_path}")

    print("\n=== VISION ===")
    vision_text = vision_observe(image_path, args.objective)
    print(vision_text)

    print("\n=== ACTION ===")
    tool_calls = action_decide(vision_text, SAMPLE_TOOLS)
    print(json.dumps(tool_calls, indent=2))

    print("\n=== GROUNDING ===")
    coords = ground_click(args.query, image_path)
    print(f"coords: {coords}")
    dot_path = annotate_and_save(image_path, coords, OUT_DIR / "grounding_dot.png")
    print(f"debug dot saved: {dot_path}")


if __name__ == "__main__":
    main()
