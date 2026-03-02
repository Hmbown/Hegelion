# Hegelion Agents Protocol

Hegelion can run as a reflexive agent loop: every action must survive an adversarial dialectic (thesis → antithesis → synthesis) before it is executed. This pattern reduces hallucinations by forcing the model to critique its own plan and propose verification steps.

## Core Loop

1. **Observe:** Receive environment state/input.
2. **Thesis (Plan A):** Propose the best next action with reasoning.
3. **Antithesis (Adversarial Critique):** Attack the plan for hallucinations, missing evidence, unsafe assumptions, and unclear validation.
4. **Synthesis (Action Decision):** Produce a single action that survives critique, plus checks/tests to de-risk it.
5. **Act:** Execute the synthesized action, log traces for preference data (optional), and repeat with the new observation.

This is adversarial reflexion: the agent refuses to act until its own critique passes.

## Prompt-Driven Implementation (No API Keys)

Hegelion ships a **prompt MCP server** (`hegelion.mcp.server`) that returns the exact prompts needed for each phase. Sequential-thinking hosts such as Cursor, Claude Desktop, or Gemini can call these tools and run the prompts with their own LLMs.

### Dialectical Workflow Tool

```python
from hegelion.core.prompt_dialectic import create_dialectical_workflow

workflow = create_dialectical_workflow(
    query="Should we subsidize fusion research?",
    use_search=True,
    use_council=True,
)
```

This returns JSON like:

```jsonc
{
  "workflow_type": "prompt_driven_dialectic",
  "steps": [
    { "step": 1, "name": "Generate Thesis", "prompt": { "phase": "thesis", ... } },
    { "step": 2, "name": "Council Critique: council_the_logician", "prompt": { ... } },
    { "step": 5, "name": "Generate Synthesis", "prompt": { "phase": "synthesis", ... } }
  ],
  "instructions": {
    "execution_mode": "sequential",
    "variable_substitution": "Replace {{thesis_from_step_1}} with the actual output",
    "final_output": "Combine all outputs into a final response"
  }
}
```

Each `prompt` entry contains:
- `phase`: thesis / antithesis / synthesis / council member
- `prompt`: the actual text to feed into the LLM
- `instructions`: how the LLM should respond
- `expected_format`: e.g., `CONTRADICTION:` / `EVIDENCE:` pairs

### Sequential Thinking (single prompt)

`create_single_shot_dialectic_prompt` returns a monolithic prompt that instructs the LLM to run Thesis → Antithesis → Synthesis by itself and format the result into:

```
## THESIS
...
## ANTITHESIS
...
## SYNTHESIS
...
```

## Why the Protocol Works

- **Adversarial Antithesis:** explicit instructions to attack hallucinations.
- **Structured Output:** prompts require `CONTRADICTION` / `EVIDENCE` fields and synthesis predictions.
- **Optional Council:** multi-perspective critiques catch gaps before action.
