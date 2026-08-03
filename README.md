# Computer Use Agent

A **vision computer-use agent** that controls a remote Linux desktop: it takes a screenshot, decides the next action, grounds clicks to screen coordinates, and acts — then observes again.

Built on [E2B Desktop Sandbox](https://github.com/e2b-dev/desktop) and inspired by [e2b-dev/open-computer-use](https://github.com/e2b-dev/open-computer-use). The loop is **see → decide → ground click → act → observe**, with a three-model pipeline (vision → action → grounding). Watch the sandbox live over E2B VNC. Models are called through [OpenRouter](https://openrouter.ai/).

## How it works

1. **Vision** — screenshot + history → what is on screen and what to do next  
2. **Action** — that description → a tool call (`click`, `type_text`, `press_key`, `run_command`, `stop`)  
3. **Grounding** — for `click`, locate `(x, y)` on the screenshot, then mouse move + click  

The loop stops when the action model calls `stop` or returns no tool call. Everything runs in an E2B sandbox so the agent does not control your local machine.

## Setup

**Prerequisites:** Python 3.10+, [Poetry](https://python-poetry.org/), [E2B API key](https://e2b.dev/dashboard?tab=keys), [OpenRouter API key](https://openrouter.ai/keys).

```sh
poetry install

cp .env.example .env
# Set E2B_API_KEY and OPENROUTER_API_KEY
```

## Run

```sh
poetry run python main.py
# Scripted desktop smoke test (no LLM):
poetry run python main.py --demo-desktop
# Later: poetry run python main.py --prompt "Open Firefox and search for the weather in San Francisco"
```

The VNC URL opens in your browser so you can watch the desktop live. Run artifacts (screenshots, logs) are written under `output/`.
