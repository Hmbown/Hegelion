# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Hegelion

Prompt-driven dialectical reasoning and autocoding system for LLMs. It generates structured prompts — it never calls LLMs itself. Two modes:

1. **Dialectical Reasoning** — Thesis → Antithesis → Synthesis (optional Council of perspectives and Judge)
2. **Autocoding (Player-Coach)** — Based on Block AI's g3 agent research. Player implements, Coach independently verifies against requirements. Requirements are the single source of truth; the Coach discards the Player's self-report.

## Build & Development Commands

```bash
# Install dependencies (uv recommended)
uv sync --dev

# Run all tests
uv run pytest -v

# Run a single test file
uv run pytest tests/test_autocoding.py -v

# Run a single test
uv run pytest tests/test_autocoding.py::test_function_name -v

# Coverage
uv run pytest --cov=hegelion --cov-report=html

# Format
uv run black hegelion tests

# Lint
uv run ruff check hegelion tests

# Run MCP server
hegelion-server              # installed entry point
python -m hegelion.mcp.server  # from source

# Self-test MCP server tools
hegelion-server --self-test
```

## Code Style

- Black formatter, line length 100. Black excludes `hegelion/engine.py` and `.gemini/`.
- Ruff linter. Both enforced in CI.
- Type hints on public functions, Google-style docstrings for public APIs.
- Pytest with `asyncio_mode = "auto"` — async test functions just work.
- Conventional commits: `feat:`, `fix(mcp):`, `docs:`, `refactor:`, `style:`, `chore:`.

## Architecture

### Core Design Principle — Prompt-Driven, No LLM Calls
The server returns structured prompts for the MCP client (Claude Desktop, Cursor, etc.) to execute. All LLM interaction happens on the client side. This means the core logic is pure prompt generation and state management — no API keys needed server-side.

### Package Layout

- **`hegelion/core/`** — Pure prompt generation and state management
  - `constants.py` — Enums: `DialecticPhase`, `AutocodingPhase`
  - `prompt_dialectic.py` — `PromptDrivenDialectic` class generates thesis/antithesis/synthesis prompts
  - `prompt_autocoding.py` — `PromptDrivenAutocoding` class generates player/coach prompts
  - `autocoding_state.py` — `AutocodingState` dataclass: stateless session state machine with save/load persistence

- **`hegelion/mcp/`** — MCP server layer
  - `server.py` — Entry point (`main()`), tool dispatcher
  - `tooling.py` — `build_tools()` returns MCP Tool definitions with schemas
  - `constants.py` — `ToolName` enum (4 tools), `MCP_SCHEMA_VERSION`
  - `validation.py` — Input validation
  - `response.py` — Response formatting
  - `handlers/dialectic.py` — Dialectic tool handlers
  - `handlers/autocoding.py` — Autocoding tool handlers

- **`hegelion/langgraph/`** — Optional LangGraph integration for durable agent loops
- **`hegelion/scripts/mcp_setup.py`** — Cross-platform MCP config generator for various hosts

### State Management
`AutocodingState` is a stateless dataclass passed explicitly between MCP tool calls. Each turn gets fresh context to prevent context pollution. State includes `schema_version` for client stability.

### Response Styles
Three output formats: `sections`, `json`, `synthesis_only` — configurable per tool call via `response_style` parameter.

### Environment Variables
- `HEGELION_LLM_COMMAND_JSON` / `HEGELION_LLM_COMMAND` — CLI command for optional server-side LLM execution
- `HEGELION_MCP_AUTO_EXECUTE=1` — Enable auto-execution mode

## CI

GitHub Actions on push to main and PRs:
- Lint (black + ruff) on Python 3.12
- Tests on Python 3.10, 3.11, 3.12
- Publish to PyPI on version tags (`v*`)
