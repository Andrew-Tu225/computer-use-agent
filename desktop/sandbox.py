"""E2B Desktop sandbox lifecycle + VNC helpers.

Create a sandbox, start E2B's built-in noVNC stream (not ffmpeg), and tear down
cleanly so viewers can watch the desktop in a normal browser tab.
"""

from __future__ import annotations

import time
from pathlib import Path

from e2b_desktop import Sandbox

_sandbox: Sandbox | None = None

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50
DEFAULT_OUTPUT_DIR = Path("output")


def _require_sandbox() -> Sandbox:
    if _sandbox is None:
        raise RuntimeError("Sandbox not created — call create_sandbox() first")
    return _sandbox


def create_sandbox(
    resolution: tuple[int, int] = (1024, 720),
    dpi: int = 96,
    timeout: int = 60,
) -> Sandbox:
    global _sandbox
    if _sandbox is not None:
        return _sandbox
    # Matches E2B computer-use docs: Sandbox.create(...).stream.start()/get_url().
    # E2B_API_KEY is read from the environment by the SDK.
    _sandbox = Sandbox.create(
        resolution=resolution,
        dpi=dpi,
        timeout=timeout,
    )
    return _sandbox


def start_sandbox_vnc() -> str:
    sandbox = _require_sandbox()
    # stream is a property returning the VNC server, not a method.
    sandbox.stream.start()
    return sandbox.stream.get_url()


def kill_sandbox() -> None:
    global _sandbox
    if _sandbox is None:
        return
    try:
        _sandbox.stream.stop()
    except Exception:
        pass
    try:
        _sandbox.kill()
    finally:
        _sandbox = None


def save_image(
    image: bytes | bytearray,
    prefix: str = "screenshot",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Write screenshot bytes to output_dir and return the path."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / f"{prefix}_{int(time.time() * 1000)}.png"
    filepath.write_bytes(bytes(image))
    return filepath


def screenshot(output_dir: str | Path = DEFAULT_OUTPUT_DIR, prefix: str = "screenshot") -> Path:
    """Capture the desktop and save a PNG under output_dir."""
    sandbox = _require_sandbox()
    image = sandbox.screenshot()
    return save_image(image, prefix=prefix, output_dir=output_dir)


def left_click(x: int, y: int) -> None:
    _require_sandbox().left_click(x, y)


def write(text: str) -> None:
    _require_sandbox().write(
        text,
        chunk_size=TYPING_GROUP_SIZE,
        delay_in_ms=TYPING_DELAY_MS,
    )


def press(key: str | list[str]) -> None:
    _require_sandbox().press(key)


def run(command: str) -> str:
    """Run a shell command in the sandbox and return combined output."""
    result = _require_sandbox().commands.run(command)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if stdout and stderr:
        return f"{stdout}\n{stderr}"
    return stdout or stderr or "The command finished running."


def launch(application: str, uri: str | None = None) -> None:
    """Launch a desktop application by name (E2B helper), optionally with a URI."""
    _require_sandbox().launch(application, uri)


def wait(ms: int) -> None:
    _require_sandbox().wait(ms)


def wait_for_desktop(timeout_s: float = 30.0) -> None:
    """Wait until the desktop UI is up (not the early blank/loading frame)."""
    sandbox = _require_sandbox()
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        # Loading frames are tiny; a real XFCE desktop screenshot is much larger.
        if len(bytes(sandbox.screenshot())) > 50_000:
            return
        sandbox.wait(500)
    raise TimeoutError(f"Desktop did not become ready within {timeout_s}s")
