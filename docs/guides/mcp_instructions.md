# Hegelion MCP Instructions for Agents

If you are an AI agent (like Claude, ChatGPT/Codex, Gemini, or a Cursor agent) connected to the Hegelion MCP server, follow these instructions to use the tools effectively.

## Core Capability

Hegelion is a **Dialectical Reasoning Engine**. It does not just "answer" questions; it forces a structured conflict between ideas to produce a higher-order truth.

## When to Use Hegelion

Use Hegelion tools when the user asks:
- High-stakes philosophical or strategic questions.
- Questions involving "truth", "bias", or "nuance".
- "Analyze this dialectically."
- "What are the contradictions in X?"
- Any query where a simple summary is insufficient and deep reasoning is required.

## Available Tools

All dialectical reasoning uses the unified `dialectic` tool with a `mode` parameter:

| Mode | Best For |
|------|----------|
| `single_shot` | Quick analysis — returns one prompt you execute |
| `workflow` | Step-by-step — returns thesis/antithesis/synthesis prompts |
| `thesis` | Manual control — get just the thesis prompt |
| `antithesis` | Manual control — critique a thesis |
| `synthesis` | Manual control — synthesize thesis + antithesis |

## Recommended: `dialectic` (mode=single_shot)

For most cases, use `dialectic` with `mode="single_shot"`. It returns a single comprehensive prompt that guides you through the entire dialectical process.

**Call the tool:**
```json
{
  "query": "Is open source software sustainable?",
  "response_style": "sections"
}
```

**Response styles:**
- `"sections"` - Full Thesis/Antithesis/Synthesis sections (default)
- `"synthesis_only"` - Just the final resolution
- `"json"` - Structured JSON with all fields (recommended for programmatic agents like Codex/ChatGPT)

**Then execute the returned prompt.** The prompt contains instructions for you to perform the dialectical reasoning.

### Server-side execution (optional)

If your MCP host does not reliably execute returned prompts (or you want `dialectic` mode=single_shot to return the final analysis directly), you can ask Hegelion to run the prompt through a backend.

**1) Configure the MCP server env:**

- `HEGELION_EXECUTION_BACKEND=auto` (recommended): prefer Codex MCP, then CLI, then prompt-only fallback
- `HEGELION_LLM_COMMAND_JSON` (preferred): a JSON array of command + args
- `HEGELION_LLM_COMMAND` (fallback): a shell-style command string
- `HEGELION_MCP_AUTO_EXECUTE=1` (optional): makes `execute` default to `true`
- `HEGELION_CODEX_MCP_COMMAND_JSON` (optional): defaults to `["codex", "mcp-server"]`
- `HEGELION_CODEX_SANDBOX=read-only` and `HEGELION_CODEX_APPROVAL_POLICY=never` are the default Codex coach settings

Example `env` using Codex CLI (reads the prompt from stdin):

```json
{
  "HEGELION_LLM_COMMAND_JSON": "[\"codex\",\"exec\",\"--sandbox\",\"read-only\",\"-\"]"
}
```

**2) Call the tool with `execute: true`:**

```json
{
  "query": "Is open source software sustainable?",
  "response_style": "sections",
  "execute": true,
  "backend": "auto"
}
```

Notes:
- `use_search: true` only adds instructions; your CLI must support tool use for real grounding.
- `backend=auto` does not hard-fail when no executable backend is available. It returns prompt-only output with metadata describing the fallback.

## Alternative: `dialectic` (mode=workflow)

For more control, use `dialectic` with `mode="workflow"`. It returns a sequence of prompts you execute in order:

```json
{
  "query": "Is open source software sustainable?",
  "mode": "workflow",
  "format": "workflow",
  "response_style": "json"
}
```

This returns:
1. A thesis prompt - execute it and save the output
2. An antithesis prompt - requires the thesis output
3. A synthesis prompt - requires both thesis and antithesis

## Presenting Results

After executing the dialectical reasoning, present it to the user:

> **Synthesis:** [The resolution that transcends both positions]
>
> **The Core Tension:** The initial view (Thesis) argued X, but the critique (Antithesis) identified that Y. The synthesis resolves this by Z.

If relevant, include:
- **Key Contradictions** found during the antithesis phase
- **Research Proposals** for further investigation

## Advanced Options

The `dialectic` tool supports optional enhancements:

- `use_search: true` — Adds instructions to use search tools for real-world grounding
- `use_council: true` — Enables multi-perspective critique (Logician, Empiricist, Ethicist)

## Autocoding Tools (Implementation Loops)

Use these when you want a player/coach loop for coding tasks:
- `autocode` — Entry point (`mode`: `init`, `workflow`, `single_shot`)
- `autocode_turn` — Execute one step (`role`: `player`, `coach`, `advance`)
- `autocode_session` — Save/load session state (`action`: `save`, `load`)

For Codex users, the intended `/hegelion` flow is:

1. Current Codex session calls `autocode_turn(role="player")` and does the implementation work.
2. Current Codex session calls `autocode_turn(role="coach", execute=true, backend="auto", cwd="<workspace>")`.
3. Treat returned `coach_feedback` as authoritative if execution succeeded.
4. Only advance the state with `autocode_turn(role="advance", coach_feedback=..., approved=...)`.

Never self-approve by answering the coach prompt in the same Codex session.
