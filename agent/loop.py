"""Agent orchestration loop: see → decide → act → observe.

Owns stepping, history, and ``run_log.md`` writing. Tool execution lives in
``agent.tools``; model calls live in ``agent.models``.
"""

from __future__ import annotations

from pathlib import Path

from agent.models import action_decide, vision_observe
from agent.tools import RunContext, TOOLS, execute, schemas_for_action
from desktop import sandbox as desktop

DEFAULT_MAX_STEPS = 25
HISTORY_KEEP = 8


def _append_log(log_path: Path, heading: str, body: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n### {heading}\n\n{body.strip()}\n")


def _history_text(entries: list[str]) -> str | None:
    if not entries:
        return None
    return "\n".join(entries[-HISTORY_KEEP:])


def run_agent_loop(
    objective: str,
    *,
    output_dir: Path,
    max_steps: int = DEFAULT_MAX_STEPS,
    ctx: RunContext | None = None,
) -> RunContext:
    """Run the vision → action → tool loop until stop, empty tools, or max steps.

    Args:
        objective: User goal for this run.
        output_dir: Directory for screenshots, red-dot images, and ``run_log.md``.
        max_steps: Safety cap on iterations.
        ctx: Optional existing context; created if omitted.

    Returns:
        The ``RunContext`` used for the run (with final step counters).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run_log.md"
    log_path.write_text(f"# Run log\n\n**Objective:** {objective}\n", encoding="utf-8")

    if ctx is None:
        ctx = RunContext(output_dir=output_dir)

    history: list[str] = []
    schemas = schemas_for_action(TOOLS)

    print(f"Available tools: {', '.join(TOOLS)}")

    for step in range(1, max_steps + 1):
        ctx.step = step
        desktop.set_timeout(120)
        print(f"\n--- step {step}/{max_steps} ---")

        shot = desktop.screenshot(
            output_dir=output_dir,
            prefix=ctx.next_image_prefix("screenshot"),
        )
        ctx.last_screenshot = shot

        thought = vision_observe(shot, objective, history=_history_text(history))
        print(f"THOUGHT:\n{thought}")
        _append_log(log_path, f"Step {step} - THOUGHT", thought)
        history.append(f"THOUGHT: {thought}")

        tool_calls = action_decide(thought, schemas)
        if not tool_calls:
            msg = "No tool call returned; stopping."
            print(msg)
            _append_log(log_path, f"Step {step} - STOP", msg)
            break

        # One tool per step (action_decide uses parallel_tool_calls=False).
        call = tool_calls[0]
        name = call.get("name") or ""
        parameters = call.get("parameters") or {}
        action_line = f"{name} {parameters}"
        print(f"ACTION: {action_line}")
        _append_log(log_path, f"Step {step} - ACTION", action_line)
        history.append(f"ACTION: {action_line}")

        # Stop semantics: end the loop without requiring further observation.
        if name == "stop":
            _append_log(log_path, f"Step {step} - OBSERVATION", "Stopped.")
            break

        observation = execute(name, parameters, ctx)
        print(f"OBSERVATION: {observation}")
        _append_log(log_path, f"Step {step} - OBSERVATION", observation)
        history.append(f"OBSERVATION: {observation}")
    else:
        msg = f"Reached max_steps ({max_steps}); stopping."
        print(msg)
        _append_log(log_path, "STOP", msg)

    return ctx
