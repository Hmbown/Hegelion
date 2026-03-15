# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Hegelion

Prompt-driven dialectical reasoning and autocoding system for LLMs. It generates structured prompts by default and can optionally execute them through MCP backends. Two modes:

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

### Core Design Principle — Prompt-Driven First, Optional Backend Execution
The default MCP behavior is still prompt generation for the client (Claude Desktop, Cursor, etc.) to execute. Server-side execution is optional and now flows through a small backend layer (`prompt`, `cli`, `codex_mcp`, `auto`) so dialectic single-shot calls and coach turns can be executed without changing the core prompt/state model.

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
  - `execution.py` — Backend selection, env/config loading, retry handling
  - `codex_mcp_backend.py` — Codex MCP stdio orchestration for independent coach execution
  - `validation.py` — Input validation
  - `response.py` — Response formatting
  - `handlers/dialectic.py` — Dialectic tool handlers
  - `handlers/autocoding.py` — Autocoding tool handlers

- **`hegelion/scripts/mcp_setup.py`** — Cross-platform MCP config generator for various hosts

### State Management
`AutocodingState` is a stateless dataclass passed explicitly between MCP tool calls. Each turn gets fresh context to prevent context pollution. State includes `schema_version` for client stability.
Backend thread/session metadata must stay out of `AutocodingState`; execution details are additive tool-output fields only.

### Response Styles
Three output formats: `sections`, `json`, `synthesis_only` — configurable per tool call via `response_style` parameter.

### Environment Variables
- `HEGELION_EXECUTION_BACKEND` — Default execution backend (`auto`, `prompt`, `cli`, `codex_mcp`)
- `HEGELION_AUTOCOACH_BACKEND` — Backend override for coach turns
- `HEGELION_LLM_COMMAND_JSON` / `HEGELION_LLM_COMMAND` — CLI command for optional server-side LLM execution
- `HEGELION_MCP_AUTO_EXECUTE=1` — Enable auto-execution mode
- `HEGELION_CODEX_MCP_COMMAND_JSON` — Codex MCP server command (defaults to `["codex", "mcp-server"]`)
- `HEGELION_CODEX_MODEL` — Optional Codex model override
- `HEGELION_CODEX_SANDBOX` — Codex sandbox mode (default: `read-only`)
- `HEGELION_CODEX_APPROVAL_POLICY` — Codex approval policy (default: `never`)

## CI

GitHub Actions on push to main and PRs:
- Lint (black + ruff) on Python 3.12
- Tests on Python 3.10, 3.11, 3.12
- Publish to PyPI on version tags (`v*`)
