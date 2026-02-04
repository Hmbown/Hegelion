# Configuration

Hegelion is prompt-driven by default. It does **not** require API keys or environment variables to generate prompts.

## Dialectical Tool Options

These options are available on `dialectical_workflow` and `dialectical_single_shot`:

- `use_search` (boolean): Instructs the prompt to use search tools before reasoning. This only affects the prompt; your host must provide search tooling.
- `use_council` (boolean): Adds Logician, Empiricist, and Ethicist critiques during antithesis.
- `use_judge` (boolean, workflow-only): Adds a final judge evaluation step.
- `execute` (boolean, single_shot-only): If true, runs the generated prompt through a configured LLM CLI and returns the model output.
- `timeout_seconds` (integer, single_shot-only): Timeout for the LLM CLI call when `execute=true` (default: 120).
- `max_retries` (integer, single_shot-only): Best-effort retries if output fails basic format validation when `execute=true` (default: 0).
- `response_style` (string): Controls output formatting.
  - `sections` (default)
  - `json`
  - `synthesis_only`
  - `conversational`
  - `bullet_points`
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

`hegelion` (autocoding entrypoint) accepts:

- `mode` (`init`, `workflow`, `single_shot`; default `workflow`)
- `max_turns` (integer, default 10)
- `approval_threshold` (float, default 0.9; `init` mode only)
- `session_name` (string, optional; `init` mode only)

`autocoding_init` accepts:

- `max_turns` (integer, default 10): Maximum player/coach turns before timeout.
- `approval_threshold` (float, default 0.9): Minimum compliance score for approval (0-1).
- `session_name` (string, optional): A human-readable session label to help track sessions.

`autocoding_advance` accepts:

- `compliance_score` (float, optional): The coach's numeric compliance score (0-1).

## MCP Host Configuration

If you install Hegelion from source instead of site-packages, the MCP config should include `PYTHONPATH` pointing at the project root. `hegelion-setup-mcp` handles this automatically.

## Health Check

Run a built-in MCP self-test to validate the server and tools:

```bash
hegelion-server --self-test
```
