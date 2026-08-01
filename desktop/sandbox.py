"""E2B Desktop sandbox lifecycle + VNC helpers.

Create a sandbox, start E2B's built-in noVNC stream (not ffmpeg), and tear down
cleanly so viewers can watch the desktop in a normal browser tab.
"""

from __future__ import annotations

from e2b_desktop import Sandbox

_sandbox: Sandbox | None = None


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
    if _sandbox is None:
        raise RuntimeError("Sandbox not created — call create_sandbox() first")
    # stream is a property returning the VNC server, not a method.
    _sandbox.stream.start()
    return _sandbox.stream.get_url()


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
