# Hegelion Specification

This document describes Hegelion's prompt-driven schemas and MCP tool outputs.

## Schema Versioning

All structured outputs include `schema_version` (currently `1`). Additive fields may appear in minor releases. Breaking changes will bump `schema_version`.

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

### `dialectical_single_shot`

Structured content:

```json
{
  "schema_version": 1,
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

### `dialectical_workflow`

Workflow response when `format="workflow"`:

```json
{
  "schema_version": 1,
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

When `format="single_prompt"`, the tool returns the same fields as `dialectical_single_shot` with `format: "single_prompt"`.

### Response Styles

Supported `response_style` values:

- `sections`
- `json`
- `synthesis_only`
- `conversational`
- `bullet_points`

When `response_style="json"`, tools include `response_schema` to define the expected JSON shape.

## Autocoding Schemas

### AutocodingState

State passed between autocoding tools:

```json
{
  "schema_version": 1,
  "session_id": "uuid",
  "session_name": "optional label",
  "requirements": "...",
  "current_turn": 0,
  "max_turns": 10,
  "phase": "player",
  "status": "active",
  "turn_history": [
    {
      "turn": 0,
      "feedback": "...",
      "approved": false,
      "score": 0.7
    }
  ],
  "last_coach_feedback": "...",
  "quality_scores": [0.7],
  "approval_threshold": 0.9
}
```

Valid `phase` values: `init`, `player`, `coach`, `approved`, `timeout`.

Valid `status` values: `active`, `approved`, `rejected`, `timeout`.

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

### Autocoding Tools

- `hegelion` is a branded entrypoint for autocoding. Use `mode: init | workflow | single_shot`.
  Responses include `entrypoint: "hegelion"` and the chosen `mode`.
- `autocoding_init` returns `AutocodingState`.
- `player_prompt` returns an `AutocodingPrompt` plus `current_phase`, `next_phase`, and an updated `state` advanced to `coach`.
- `coach_prompt` returns an `AutocodingPrompt` plus `current_phase`, `next_phase`, and a `state` still in `coach` (for `autocoding_advance`).
- `autocoding_advance` returns the next `AutocodingState`.
- `autocoding_single_shot` returns an `AutocodingPrompt`.
- `autocoding_save` and `autocoding_load` persist and restore `AutocodingState`.

## Error Responses

When a tool fails validation, the MCP response includes structured error metadata:

```json
{
  "schema_version": 1,
  "tool": "player_prompt",
  "error": "Invalid phase: coach",
  "expected": "player",
  "received": "coach",
  "hint": "If you just called autocoding_init or autocoding_advance, pass that returned state into player_prompt."
}
```

Error responses may include `expected` and `received` fields when input validation fails.
