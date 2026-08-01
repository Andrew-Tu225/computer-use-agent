"""Create an E2B Desktop sandbox, open the VNC stream, wait, then tear down."""

from __future__ import annotations

import webbrowser

from dotenv import load_dotenv

from desktop.sandbox import create_sandbox, kill_sandbox, start_sandbox_vnc


def main() -> None:
    load_dotenv()
    sandbox = None
    try:
        print("Creating E2B Desktop sandbox...")
        sandbox = create_sandbox()
        print(f"Sandbox ready: {sandbox.sandbox_id}")

        print("Starting VNC stream...")
        vnc_url = start_sandbox_vnc()
        print(f"VNC URL: {vnc_url}")
        webbrowser.open(vnc_url)

        input("Sandbox is live. Press Enter to stop and kill it...\n")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        print("Stopping sandbox...")
        kill_sandbox()
        print("Done.")


if __name__ == "__main__":
    main()
