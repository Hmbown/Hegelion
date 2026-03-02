# Configuration

Hegelion is prompt-driven by default. It does **not** require API keys or environment variables to generate prompts.

## Dialectical Tool Options

These options are available on the unified `dialectic` tool:

- `mode` (string): Selects the dialectical mode.
  - `single_shot` — Returns one prompt covering thesis → antithesis → synthesis.
  - `workflow` — Returns a step-by-step workflow of separate prompts.
  - `thesis` / `antithesis` / `synthesis` — Individual phase prompts for manual control.
- `use_search` (boolean): Instructs the prompt to use search tools before reasoning. This only affects the prompt; your host must provide search tooling.
- `use_council` (boolean): Adds Logician, Empiricist, and Ethicist critiques during antithesis.
- `execute` (boolean, single_shot-only): If true, runs the generated prompt through a configured LLM CLI and returns the model output.
- `timeout_seconds` (integer, single_shot-only): Timeout for the LLM CLI call when `execute=true` (default: 120).
- `max_retries` (integer, single_shot-only): Best-effort retries if output fails basic format validation when `execute=true` (default: 0).
- `response_style` (string): Controls output formatting.
  - `sections` (default)
  - `json`
  - `synthesis_only`
- `format` (workflow-only):
  - `workflow` (default): returns a step-by-step workflow
  - `single_prompt`: returns a single consolidated prompt

When `response_style` is `json`, the MCP response includes a `response_schema` that describes the expected JSON shape.

### CLI Execution Configuration (Optional)

To use `execute=true` without server-side API keys, configure one of:

- `HEGELION_LLM_COMMAND_JSON`: JSON array of command + args (preferred)
- `HEGELION_LLM_COMMAND`: shell-style command string (fallback)
- `HEGELION_MCP_AUTO_EXECUTE=1`: makes `execute` default to `true` when omitted

The prompt is sent to the CLI on stdin, and the CLI's stdout becomes the tool result.

## Autocoding Tool Options

Four unified tools replace the previous API:

**`autocode`** — Entry point for autocoding sessions:

- `mode` (`init`, `workflow`, `single_shot`; default `workflow`)
- `max_turns` (integer, default 10; `init` mode only)
- `session_name` (string, optional; `init` mode only)

**`autocode_turn`** — Execute one step in the autocoding loop:

- `role` (`player`, `coach`, `advance`)
- `state` (AutocodingState JSON from previous tool call)
- `coach_feedback` (string; required when `role=advance`)
- `approved` (boolean; required when `role=advance`)

**`autocode_session`** — Persist or restore session state:

- `action` (`save`, `load`)
- `state` (AutocodingState JSON; required for `save`)
- `filepath` (string; path to session JSON file)

## MCP Host Configuration

If you install Hegelion from source instead of site-packages, the MCP config should include `PYTHONPATH` pointing at the project root. `hegelion-setup-mcp` handles this automatically.

## Health Check

Run a built-in MCP self-test to validate the server and tools:

```bash
hegelion-server --self-test
```
