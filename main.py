"""Create an E2B Desktop sandbox, open the VNC stream, wait, then tear down."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from desktop.sandbox import (
    create_sandbox,
    kill_sandbox,
    launch,
    press,
    screenshot,
    start_sandbox_vnc,
    wait,
    wait_for_desktop,
    write,
)

DEMO_OUTPUT = Path("output/demo_desktop")


def run_desktop_demo() -> None:
    """No-LLM smoke test: open Chrome, type a URL, save screenshots."""
    wait_for_desktop()
    screenshot(output_dir=DEMO_OUTPUT, prefix="before")

    # Firefox does not open a window on this E2B desktop image; Chrome does.
    launch("google-chrome", "https://example.com")
    wait(4000)
    screenshot(output_dir=DEMO_OUTPUT, prefix="after_launch")

    press(["ctrl", "l"])
    wait(500)
    write("https://example.com")
    press("enter")
    wait(3000)
    screenshot(output_dir=DEMO_OUTPUT, prefix="after_nav")
    print(f"Screenshots saved under {DEMO_OUTPUT}/")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Computer Use Agent sandbox runner")
    parser.add_argument(
        "--demo-desktop",
        action="store_true",
        help="Run scripted Chrome control demo (no LLM)",
    )
    args = parser.parse_args()

    try:
        print("Creating E2B Desktop sandbox...")
        sandbox = create_sandbox(timeout=300 if args.demo_desktop else 60)
        print(f"Sandbox ready: {sandbox.sandbox_id}")

        vnc_url = start_sandbox_vnc()
        print(f"VNC URL: {vnc_url}")
        webbrowser.open(vnc_url)

        if args.demo_desktop:
            run_desktop_demo()

        try:
            input("Press Enter to stop and kill the sandbox...\n")
        except EOFError:
            pass
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        print("Stopping sandbox...")
        kill_sandbox()
        print("Done.")


if __name__ == "__main__":
    main()
