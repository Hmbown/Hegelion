# MCP Integration

Hegelion works as an MCP (Model Context Protocol) server. It returns structured prompts that your existing LLM executes—no extra API keys required.

## How It Works

When you use Hegelion via MCP, the server generates prompts for each dialectical phase. Your editor's model (Claude, GPT, Gemini, etc.) runs them. Hegelion never makes API calls in this mode.

```
Your Editor (Cursor, Claude Desktop, VS Code)
    │
    ▼
Hegelion MCP Server (generates prompts)
    │
    ▼
Your LLM (executes the prompts)
```

## Installation

```bash
pip install hegelion

# If running from source:
pip install -e .
```

## Supported Environments

| Environment | Config Location | Setup |
|-------------|-----------------|-------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) | [Auto](#claude-desktop) or [Manual](#claude-desktop-1) |
| Claude Code | `~/.claude.json` | [CLI](#claude-code) |
| Cursor | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project) | [Auto](#cursor) or [Manual](#cursor) |
| VS Code + Copilot | `.vscode/mcp.json` | [Auto](#vs-code--github-copilot) or [Manual](#vs-code--github-copilot) |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | [Auto](#windsurf) or [Manual](#windsurf) |
| Google Antigravity | MCP Store → Manage → `mcp_config.json` | [Manual](#google-antigravity) |
| Gemini CLI | Extension install | [CLI](#gemini-cli) |

## Quick Start

If you use Claude Desktop, Cursor, VS Code, or Windsurf, run the host shortcut:

```bash
hegelion-setup-mcp --host claude-desktop
hegelion-setup-mcp --host cursor
hegelion-setup-mcp --host vscode
hegelion-setup-mcp --host windsurf
```

## Setup by Environment

### Claude Desktop

**Auto-config (recommended):**

```bash
# Shortcut (auto-detects OS)
hegelion-setup-mcp --host claude-desktop

# macOS
hegelion-setup-mcp --write "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Windows
hegelion-setup-mcp --write "%APPDATA%\Claude\claude_desktop_config.json"

# Linux
hegelion-setup-mcp --write "$HOME/.config/Claude/claude_desktop_config.json"
```

**Manual config:**

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/full/path/to/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

Find your Python path:
```bash
which python
# Example: /usr/local/bin/python
```

**Restart required:** Quit Claude Desktop completely (Cmd+Q on macOS) and reopen.

### Claude Code

```bash
# Add the MCP server
claude mcp add hegelion python -- -m hegelion.mcp.server

# Verify
claude mcp list

# Restart Claude Code
exit  # Then reopen terminal
```

### Cursor

Cursor supports MCP with up to 40 tools. Config can be global or project-specific.

**Auto-config shortcut:**

```bash
hegelion-setup-mcp --host cursor
```

**Option 1: Global config** (all projects)

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/full/path/to/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

**Option 2: Project config**

Create `.cursor/mcp.json` in your project root with the same JSON.

**Option 3: Settings UI**

1. Go to **File → Preferences → Cursor Settings**
2. Select **MCP** option
3. Paste the JSON config

After adding, restart Cursor.

### VS Code + GitHub Copilot

VS Code 1.99+ supports MCP natively with GitHub Copilot. MCP is generally available starting from VS Code 1.102.

> **Note:** For Copilot Business/Enterprise, the "MCP servers in Copilot" policy must be enabled by your org admin.

**Auto-config shortcut:**

```bash
hegelion-setup-mcp --host vscode
```

Create `.vscode/mcp.json` in your project:

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/full/path/to/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

A "Start" button will appear in the file. Click it to start the MCP server.

For more details, see [VS Code MCP documentation](https://code.visualstudio.com/docs/copilot/customization/mcp-servers).

### Windsurf

Windsurf (Codeium's IDE) supports MCP through its Cascade AI assistant.

**Auto-config shortcut:**

```bash
hegelion-setup-mcp --host windsurf
```

1. Open **Windsurf Settings** (Cmd+Shift+P → "Open Windsurf Settings")
2. Go to the **Cascade** section
3. Scroll to **MCP Servers**
4. Or directly edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/full/path/to/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

Press the refresh button after adding. Windsurf supports up to 100 tools.

For more details, see [Windsurf MCP documentation](https://docs.windsurf.com/windsurf/cascade/mcp).

### Google Antigravity

Google's agent-first IDE (released November 2025) has a built-in MCP Store.

1. Click **Agent session** → **"..."** dropdown → **MCP Servers**
2. Select **Manage MCP Servers** at the top
3. Click **View raw config** to edit `mcp_config.json`:

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/full/path/to/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

For more details, see [Antigravity MCP guide](https://medium.com/@jaintarun7/google-antigravity-custom-mcp-server-integration-to-improve-vibe-coding-f92ddbc1c22d).

### Gemini CLI

```bash
gemini extensions install https://github.com/Hmbown/Hegelion --branch main --path hegelion-mcp-node
```

## Available Tools

### `dialectic`

Unified dialectical reasoning tool. Use `mode` to select the operation:

**mode=single_shot** (default) — Returns one prompt that guides the LLM through Thesis → Antithesis → Synthesis.

```
Use Hegelion's dialectic with mode=single_shot to analyze: "Can AI be creative?"
```

Optional: single-call CLI execution (no server-side API keys). Configure the server with `HEGELION_LLM_COMMAND_JSON`
and call with `execute: true` to return the final analysis directly.

**mode=workflow** — Returns a structured workflow for step-by-step execution. Use for complex queries.

```
Use Hegelion's dialectic with mode=workflow for: "Should we regulate AI?" with use_council=true
```

**mode=thesis / antithesis / synthesis** — Individual phase prompts for manual control.

### Autocoding Tools (v0.5.0+)

Four unified tools for the player-coach loop:

| Tool | Purpose |
|------|---------|
| `autocode` | Entry point (`mode`: `init`, `workflow`, `single_shot`) |
| `autocode_turn` | Execute one step (`role`: `player`, `coach`, `advance`) |
| `autocode_session` | Save/load session state (`action`: `save`, `load`) |

**State passing + schema:**
- Tool outputs include `schema_version` for client-side stability.
- `autocode` (mode=init) returns an `AutocodingState` with `phase: "player"`.
- `autocode_turn` (role=player) returns the player prompt plus a `state` already advanced to `phase: "coach"` for the next call.
- `autocode_turn` (role=coach) returns the coach prompt with the same `state` (still `phase: "coach"`) for the advance step.
- `autocode_turn` (role=advance) advances state after coach review (requires `coach_feedback` and `approved`).

**Example:**
```
Use autocode with mode=init and these requirements:
- Add user authentication to src/api.py
- Add tests in tests/test_auth.py
- All tests must pass
```

## Feature Toggles

| Option | Default | Description |
|--------|---------|-------------|
| `use_council` | `false` | Activates three critics: Logician, Empiricist, Ethicist |
| `use_search` | `false` | Prompts include search grounding instructions |
| `response_style` | `sections` | Output format: `json`, `sections`, or `synthesis_only` |

**Example with options:**
```
Run dialectic mode=single_shot on "Is consciousness fundamental?" with use_council=true
```

## Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `spawn hegelion-server ENOENT` | `hegelion-server` not in PATH | Use `python -m hegelion.mcp.server` |
| `ModuleNotFoundError: hegelion` | Running from source without install | Run `pip install -e .` from repo root |
| Server disconnects on startup | Python path issues | Use full path (see below) |
| "Unknown tool" error | Config not loaded | Restart your editor completely |

### Finding Your Python Path

**Standard:**
```bash
which python
which python3
```

**Pyenv:**
```bash
pyenv which python
# Example: /Users/you/.pyenv/versions/3.11.9/bin/python
```

**Conda:**
```bash
conda list python | grep python
```

**Virtual environment:**
```bash
# With env activated:
which python
# Example: /path/to/venv/bin/python
```

### Checking Logs

**macOS:**
```bash
cat ~/Library/Logs/Claude/mcp-server-hegelion.log
```

**Windows:**
```cmd
type %APPDATA%\Claude\logs\mcp-server-hegelion.log
```

**Linux:**
```bash
cat ~/.local/share/Claude/logs/mcp-server-hegelion.log
```

### Sample Configurations

**Standard (Homebrew Python):**
```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/usr/local/bin/python3",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

**Pyenv:**
```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/Users/you/.pyenv/versions/3.11.9/bin/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

**Conda:**
```json
{
  "mcpServers": {
    "hegelion": {
      "command": "/Users/you/miniconda3/bin/python",
      "args": ["-m", "hegelion.mcp.server"]
    }
  }
}
```

## Verifying Installation

After setup, ask in your editor:

> "What Hegelion tools are available?"

You should see:
- **Dialectical:** `dialectic`
- **Autocoding:** `autocode`, `autocode_turn`, `autocode_session`

## Getting Help

If you're stuck:
1. Check the log file (see above)
2. Ensure you used full Python path
3. Verify `pip install hegelion` completed
4. Open an issue at [github.com/Hmbown/Hegelion](https://github.com/Hmbown/Hegelion/issues)
