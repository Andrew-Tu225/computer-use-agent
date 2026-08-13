"""Thin facade around the agent loop — one ``run(objective)`` entry point.

Holds run-directory allocation and delegates stepping to ``agent.loop``.
"""

from __future__ import annotations

from pathlib import Path

from agent.loop import DEFAULT_MAX_STEPS, run_agent_loop
from agent.tools import RunContext
from desktop import sandbox as desktop

DEFAULT_OUTPUT_ROOT = Path("output")


def allocate_run_dir(root: Path | str = DEFAULT_OUTPUT_ROOT) -> Path:
    """Create the next ``output/run_N/`` directory and return it."""
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    n = 1
    while (base / f"run_{n}").exists():
        n += 1
    path = base / f"run_{n}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class ComputerAgent:
    """Facade: allocate a run folder and execute the see → decide → act loop."""

    def __init__(
        self,
        output_root: Path | str = DEFAULT_OUTPUT_ROOT,
        *,
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        self.output_root = Path(output_root)
        self.max_steps = max_steps
        self.last_run_dir: Path | None = None
        self.last_ctx: RunContext | None = None

    def run(self, objective: str) -> Path:
        """Run the agent on ``objective``; return the run output directory.

        Ensures the desktop is ready, then calls ``run_agent_loop``.
        """
        run_dir = allocate_run_dir(self.output_root)
        self.last_run_dir = run_dir
        print(f"Run artifacts: {run_dir}")

        desktop.wait_for_desktop()
        self.last_ctx = run_agent_loop(
            objective,
            output_dir=run_dir,
            max_steps=self.max_steps,
        )
        print(f"\nFinished. Log: {run_dir / 'run_log.md'}")
        return run_dir
