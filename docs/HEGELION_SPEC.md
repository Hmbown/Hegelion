# Hegelion Specification

This document describes Hegelion's prompt-driven schemas and MCP tool outputs.

## Schema Versioning

All structured outputs include `schema_version` (currently `2`). Additive fields may appear in minor releases. Breaking changes will bump `schema_version`.

## Dialectical Reasoning Schemas

### DialecticalPrompt

Shared structure for thesis/antithesis/synthesis prompts:

```json
{
  "phase": "thesis",
  "prompt": "...",
  "instructions": "...",
  "expected_format": "..."
}
```

### `dialectic` (mode=single_shot)

Structured content:

```json
{
  "schema_version": 2,
  "query": "...",
  "use_search": false,
  "use_council": false,
  "response_style": "sections",
  "mode": "prompt",
  "prompt": "...",
  "response_schema": { "optional": true }
}
```

`response_schema` appears when `response_style="json"`.

Optional CLI execution:

If `execute=true` is passed (or `HEGELION_MCP_AUTO_EXECUTE=1` is set) *and* the server is configured with
`HEGELION_LLM_COMMAND_JSON` (preferred) or `HEGELION_LLM_COMMAND`, the tool runs the generated prompt through that CLI.

In this mode, `content[0].text` is the model output (not the prompt), and structured content adds:

```json
{
  "mode": "executed",
  "llm_cli": "codex",
  "timeout_seconds": 120,
  "max_retries": 0,
  "attempts": 1,
  "returncode": 0,
  "output": "...",
  "stderr": { "optional": true },
  "validation_error": { "optional": true }
}
```

### `dialectic` (mode=workflow)

Workflow response when `format="workflow"`:

```json
{
  "schema_version": 2,
  "query": "...",
  "workflow_type": "prompt_driven_dialectic",
  "steps": [
    {
      "step": 1,
      "name": "Generate Thesis",
      "prompt": { "phase": "thesis", "prompt": "...", "instructions": "...", "expected_format": "..." }
    }
  ],
  "instructions": {
    "execution_mode": "sequential",
    "variable_substitution": "Replace {{variable_name}} with actual outputs",
    "final_output": "Combine all outputs into a final response",
    "response_style": "sections",
    "response_style_note": "...",
    "response_schema": { "optional": true },
    "phase_schemas": { "optional": true }
  }
}
```

When `format="single_prompt"`, the tool returns the same fields as `dialectic` mode=single_shot with `format: "single_prompt"`.

### `dialectic` (mode=thesis/antithesis/synthesis)

Individual phase prompts for step-by-step dialectic. Returns a `DialecticalPrompt` with `schema_version`, `phase`, `prompt`, `instructions`, `expected_format`, and `response_style`.

### Response Styles

Supported `response_style` values:

- `sections` — Full structured output with labeled sections
- `json` — Machine-readable JSON (includes `response_schema`)
- `synthesis_only` — Only the synthesis/resolution

When `response_style="json"`, tools include `response_schema` to define the expected JSON shape.

## Autocoding Schemas

### AutocodingState

State passed between autocoding tools:

```json
{
  "schema_version": 2,
  "session_id": "uuid",
  "session_name": "optional label",
  "requirements": "...",
  "current_turn": 0,
  "max_turns": 10,
  "phase": "player",
  "turn_history": [
    {
      "turn": 0,
      "feedback": "...",
      "approved": false
    }
  ],
  "last_coach_feedback": "..."
}
```

Valid `phase` values: `player`, `coach`, `approved`, `timeout`.

### AutocodingPrompt

```json
{
  "phase": "player",
  "prompt": "...",
  "instructions": "...",
  "expected_format": "...",
  "requirements_embedded": true
}
```

### Autocoding Tools (v0.5.0 Unified)

Four unified tools replace the previous 14-tool API:

- **`autocode`** — Entry point for autocoding sessions.
  - `mode=init`: Create a new session, returns `AutocodingState`.
  - `mode=workflow`: Generate a structured step-by-step recipe as JSON.
  - `mode=single_shot`: Generate a single combined player+coach prompt.
- **`autocode_turn`** — Execute one step in the autocoding loop.
  - `role=player`: Generate implementation prompt, advances state to `coach` phase.
  - `role=coach`: Generate verification prompt for current turn.
  - `role=advance`: Advance state after coach review (requires `coach_feedback` and `approved`).
- **`autocode_session`** — Persist or restore session state.
  - `action=save`: Save `AutocodingState` to a JSON file.
  - `action=load`: Restore `AutocodingState` from a JSON file.

## Error Responses

When a tool fails validation, the MCP response includes structured error metadata:

```json
{
  "schema_version": 2,
  "tool": "autocode_turn",
  "error": "Invalid phase: coach",
  "expected": "player",
  "received": "coach",
  "hint": "If you just called autocode (mode=init) or autocode_turn (role=advance), pass that returned state into autocode_turn role=player."
}
```

Error responses may include `expected` and `received` fields when input validation fails.
