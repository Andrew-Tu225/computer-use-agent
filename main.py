"""Create an E2B Desktop sandbox, open the VNC stream, run demos or the agent."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from agent.agent import ComputerAgent
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
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Run the vision→action→grounding agent with this objective",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=25,
        help="Maximum agent loop iterations (default: 25)",
    )
    args = parser.parse_args()

    if args.demo_desktop and args.prompt:
        parser.error("Use only one of --demo-desktop or --prompt")

    # Agent / demo runs need a longer initial lease; the loop also refreshes timeout.
    needs_long_timeout = bool(args.demo_desktop or args.prompt)

    try:
        print("Creating E2B Desktop sandbox...")
        sandbox = create_sandbox(timeout=600 if needs_long_timeout else 60)
        print(f"Sandbox ready: {sandbox.sandbox_id}")

        vnc_url = start_sandbox_vnc()
        print(f"VNC URL: {vnc_url}")
        webbrowser.open(vnc_url)

        if args.demo_desktop:
            run_desktop_demo()
        elif args.prompt:
            ComputerAgent(max_steps=args.max_steps).run(args.prompt)

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
