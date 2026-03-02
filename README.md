# Hegelion

> "The True is the whole." — G.W.F. Hegel

Hegelion applies dialectical reasoning to LLMs: forcing models to argue with themselves before reaching conclusions. This produces better reasoning for questions and better code for implementations.

Hegelion is prompt-driven by default: it generates prompts for your editor or LLM to execute, with no API keys required.
Use it via MCP in editors like Claude Desktop/Cursor/VS Code, or via the Python API in your own agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg) [![PyPI version](https://img.shields.io/pypi/v/hegelion.svg)](https://pypi.org/project/hegelion/)

---

## Two Modes

| Mode | Pattern | Use Case |
|------|---------|----------|
| **Dialectical Reasoning** | Thesis → Antithesis → Synthesis | Deep analysis of questions, philosophy, strategy |
| **Autocoding** | Player → Coach → Iterate | Verified code implementations with independent review |

Both modes use the same principle: **force the model to oppose itself** before concluding. This catches blind spots that single-pass approaches miss.

---

## Autocoding: Player-Coach Loop

**Updated in v0.5.0** — Based on [Block AI's g3 agent research](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf).

### The Problem

Single-agent coding tools often:
- Declare success prematurely ("I have successfully implemented all requirements!")
- Accumulate context pollution over long sessions
- Miss edge cases because they verify their own work

### The Solution

Two roles iterate until requirements are verified:

```
REQUIREMENTS (Source of Truth)
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│    PLAYER     │────▶│     COACH     │────▶│    ADVANCE    │
│  Implements   │     │   Verifies    │     │    State      │
│  code & tests │     │ independently │     │               │
└───────────────┘     └───────────────┘     └───────┬───────┘
        ▲                                           │
        │              ┌───────────┐                │
        └──────────────│ APPROVED? │◀───────────────┘
                       └───────────┘
                         │       │
                        No      Yes
                         │       │
                         ▼       ▼
                     Continue   Done
```

**Player**: Implements requirements, writes tests, responds to feedback. Does NOT declare success.

**Coach**: Independently verifies each requirement, ignores player's self-assessment, outputs structured checklist.

### Key Insight

> "Discard the player's self-report of success. Have the coach perform independent evaluation."

The coach catches issues by re-reading requirements and actually running tests—not by trusting what the player says it did.

### Quick Start (Autocoding)

In Claude Code, Cursor, or any MCP-enabled editor:

Tip: if your editor exposes slash commands, you can use `/hegelion` as a wrapper.
The underlying MCP tools are `autocode` and `autocode_turn`.

```
You: Call autocode with mode=init and these requirements:
     - Add user authentication to src/api.py
     - Add tests in tests/test_auth.py
     - All tests must pass

[Session initializes]

You: Call autocode_turn with role=player and implement

[Player writes code and tests]

You: Call autocode_turn with role=coach and verify

[Coach: ✓ auth endpoint exists, ✗ missing password validation test]

You: Call autocode_turn with role=advance, coach_feedback, approved=false

[Loop until COACH APPROVED]
```

**State passing note:** `autocode_turn` with `role=player` returns a player prompt plus an updated `state` advanced to `phase: "coach"` for the next call. Prompt outputs include `current_phase` (prompt phase) and `next_phase` (returned state's phase). All structured outputs include `schema_version` for client stability.

### MCP Tools

| Tool | Purpose |
|------|---------|
| `dialectic` | Unified dialectical reasoning (`mode`: `single_shot`, `workflow`, `thesis`, `antithesis`, `synthesis`) |
| `autocode` | Unified autocoding entrypoint (`mode`: `init`, `workflow`, `single_shot`) |
| `autocode_turn` | Execute one autocoding turn (`role`: `player`, `coach`, `advance`) |
| `autocode_session` | Persist or restore sessions (`action`: `save`, `load`) |

### Codex Skill (optional)

This repo includes a Codex skill at `skills/hegelion/SKILL.md`. Install it with your skill
installer (for example, `install-skill-from-github.py --repo Hmbown/Hegelion --path skills/hegelion`).
It mirrors the `/hegelion` command and uses MCP tools when available.

### Why It Works

| Problem | Single Agent | Coach-Player |
|---------|--------------|--------------|
| **Anchoring** | Drifts from requirements | Requirements anchor every turn |
| **Verification** | Self-assessment (unreliable) | Independent verification |
| **Context** | Accumulates pollution | Fresh context each turn |
| **Completion** | Open-ended | Explicit approval gates |

---

## Dialectical Reasoning: Thesis → Antithesis → Synthesis

For questions requiring deep analysis, Hegelion forces three separate LLM calls:

```
[Call 1] Thesis     → LLM commits to a position
[Call 2] Antithesis → LLM attacks that position (separate call, no hedging)
[Call 3] Synthesis  → LLM reconciles the opposition
```

### Why Separate Calls Matter

| Method | Calls | Result |
|--------|:-----:|--------|
| **Raw** | 1 | "It depends on definitions..." |
| **Enhanced** | 1 | "Hold both views in tension..." |
| **Hegelion** | 3 | Novel framework with testable predictions |

When the model must commit to a thesis, then genuinely attack it in a separate call, the synthesis surfaces insights that single-call approaches shortcut.

<details>
<summary><b>Example: "Is free will compatible with determinism?"</b></summary>

**Hegelion synthesis** (after thesis and antithesis):

> The deadlock dissolves when we recognize free will exists on a **spectrum of self-authorship**:
>
> 1. **Minimal freedom**: Acting on desires without external coercion
> 2. **Reflective freedom**: Second-order endorsement—I want to want this
> 3. **Narrative freedom**: Acting consistently with a coherent life narrative
> 4. **Constitutive freedom**: Recursive self-modification through deliberate habituation
>
> **Research proposal**: Use fMRI to scan participants under (1) snap judgments, (2) brief reflection, (3) extended deliberation. Hypothesis: Condition (3) shows strongest correlation with self-reported decision "ownership."

This 4-level framework emerged from actually arguing with itself—not from asking for "thesis/antithesis/synthesis" in one prompt.
</details>

### Quick Start (Dialectical)

```bash
pip install hegelion

# MCP setup (auto-detects OS)
hegelion-setup-mcp --host claude-desktop

# MCP setup for Claude Desktop (macOS)
hegelion-setup-mcp --write "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

Or use the prompt-driven Python API (you run the prompt with your LLM of choice):

```python
from hegelion.core.prompt_dialectic import create_single_shot_dialectic_prompt

prompt = create_single_shot_dialectic_prompt(
    "Is AI conscious?",
    use_council=True,
    response_style="sections",
)
print(prompt)
```

Health check (lists tools + generates a sample prompt):

```bash
hegelion-server --self-test
```

### Feature Toggles

| Option | Description |
|--------|-------------|
| `use_council` | Three critics: Logician, Empiricist, Ethicist |
| `use_search` | Grounds arguments with web search |
| `response_style` | `sections`, `json`, or `synthesis_only` |

---

## Installation

```bash
pip install hegelion
```

For MCP integration (works with any MCP-enabled editor):

```bash
# Shortcuts
hegelion-setup-mcp --host claude-desktop
hegelion-setup-mcp --host cursor
hegelion-setup-mcp --host vscode
hegelion-setup-mcp --host windsurf

# Claude Desktop (macOS)
hegelion-setup-mcp --write "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Claude Desktop (Windows)
hegelion-setup-mcp --write "%APPDATA%\\Claude\\claude_desktop_config.json"

# Claude Desktop (Linux)
hegelion-setup-mcp --write "$HOME/.config/Claude/claude_desktop_config.json"

# Then restart your MCP host
```

Claude Code (no MCP setup needed):

```bash
# Use /hegelion command directly in any Hegelion repo clone
# Or add MCP server for tool access
claude mcp add hegelion python -- -m hegelion.mcp.server
```

Manual config (any MCP host):

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

If you run from source (not site-packages), set `PYTHONPATH` to the repo root. The `hegelion-setup-mcp` command writes this automatically.
If your host expects a full command path, use `python -m hegelion.mcp.server` instead of `hegelion-server`.

**Supported editors:** Claude Desktop, Claude Code, Cursor, VS Code + GitHub Copilot, Windsurf, Google Antigravity, Gemini CLI

See [MCP Integration Guide](docs/guides/mcp-integration.md) for setup instructions.

---

## Documentation

- **[MCP Integration](docs/guides/mcp-integration.md)** — Setup for Claude Desktop, Cursor, VS Code + Copilot, Windsurf, Antigravity, Gemini CLI
- **[Python API](docs/guides/python-api.md)** — Prompt-driven API reference
- **[CLI Reference](docs/guides/cli-reference.md)** — MCP server and setup commands
- **[Configuration](docs/getting-started/configuration.md)** — Backends and feature toggles
- **[Technical Specification](docs/HEGELION_SPEC.md)** — Output schemas, phase specs

---

## Contributing

Issues and PRs welcome. For significant changes, open a discussion first.

---

## Recent Changes

### v0.5.0 (March 2026)

- **MCP tool consolidation**: 14 tools simplified to 4 unified tools: `dialectic`, `autocode`, `autocode_turn`, `autocode_session`
- **State machine simplification**: `AutocodingStatus` removed; `phase` is now the only state indicator
- **Schema migration**: `schema_version` bumped to `2` with backward-compatible v1-to-v2 loading
- **Validation cleanup**: Added `@validated` decorator + typed specs to remove repetitive handler boilerplate
- **Dead code removal**: Removed unused judge path, unused conversation state, and deprecated response styles
- **Python 3.13 support**: Added to CI and classifiers
- **Public API exports**: `hegelion` now exports key classes directly (`DialecticalPrompt`, `PromptDrivenDialectic`, `AutocodingState`, etc.)
- **PEP 561 `py.typed` marker**: Enables type-checker support for library consumers
- **`--version` flag**: Both `hegelion-server` and `hegelion-setup-mcp` now support `--version`
- **Updated model references**: `.env.example` modernized (Claude Sonnet 4.6, GPT-5.2, Gemini 3 Pro)
- **CHANGELOG fix**: Corrected malformed duplicate section headers

### v0.4.6 (February 4, 2026)

- **CI fix**: Fixed CI pipeline and automated release workflow

### v0.4.5 (February 4, 2026)

- **Single-call CLI execution** for `dialectical_single_shot`: `execute`, `timeout_seconds`, `max_retries`
- **`hegelion-setup-mcp` flags**: `--llm-command-json`, `--llm-command`, `--auto-execute`

### v0.4.4 (January 21, 2026)

- **Simplified skill/command**: Condensed to minimal routing tables, MCP-first approach

### v0.4.3 (January 12, 2026)

- **MCP refactor**: Split tooling, handlers, and validation to make the server easier to extend and maintain
- **Codex skill**: Added `skills/hegelion/SKILL.md` for the `/hegelion` workflow

---

**License:** MIT
