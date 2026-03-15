# Python API

Hegelion's Python API is prompt-driven. It **does not call an LLM for you**; it generates structured prompts you run with your model of choice.
Server-side execution backends such as `cli` and `codex_mcp` are exposed through the MCP server layer, not the pure Python prompt helpers.

Minimal example: `examples/hello_world_prompt.py`.

## Dialectical Prompts (Thesis → Antithesis → Synthesis)

Use the prompt helpers to generate either a single prompt or a step-by-step workflow.

### Single prompt

```python
from hegelion.core.prompt_dialectic import create_single_shot_dialectic_prompt

query = "Should cities ban short-term rentals?"
prompt = create_single_shot_dialectic_prompt(
    query=query,
    use_council=True,
    response_style="sections",
)
print(prompt)
```

### Step-by-step prompts

```python
from hegelion.core.prompt_dialectic import PromptDrivenDialectic

dialectic = PromptDrivenDialectic()

thesis_prompt = dialectic.generate_thesis_prompt(
    "Is AI conscious?",
    response_style="sections",
)

# Send thesis_prompt.prompt to your LLM, then capture its output as `thesis_output`.

antithesis_prompt = dialectic.generate_antithesis_prompt(
    "Is AI conscious?",
    thesis_output,
    use_search_context=False,
    response_style="sections",
)

# Send antithesis_prompt.prompt, capture `antithesis_output`.

synthesis_prompt = dialectic.generate_synthesis_prompt(
    "Is AI conscious?",
    thesis_output,
    antithesis_output,
    response_style="sections",
)

# Send synthesis_prompt.prompt to your LLM for the final synthesis.
```

### Response styles

Supported `response_style` values:

- `sections` (default)
- `json`
- `synthesis_only`

When you use `json`, the prompt includes explicit JSON shape instructions.

## Autocoding (Player → Coach Loop)

Use the state machine to keep player/coach turns synchronized across calls.

```python
from hegelion.core.autocoding_state import AutocodingState
from hegelion.core.prompt_autocoding import PromptDrivenAutocoding

requirements = """## Requirements\n- [ ] Add auth endpoint\n- [ ] Add tests\n"""

state = AutocodingState.create(
    requirements=requirements,
    max_turns=5,
    session_name="auth-feature",
)

autocoding = PromptDrivenAutocoding()

player_prompt = autocoding.generate_player_prompt(
    requirements=state.requirements,
    coach_feedback=state.last_coach_feedback,
    turn_number=state.current_turn + 1,
    max_turns=state.max_turns,
)

# Send player_prompt.prompt to your LLM, implement changes.
# Then run the coach prompt and advance the state based on its feedback.
```

## Workflows for Orchestration

If you need a machine-readable recipe to drive an agent loop, use the workflow builders:

```python
from hegelion.core.prompt_dialectic import create_dialectical_workflow
from hegelion.core.prompt_autocoding import create_autocoding_workflow

workflow = create_dialectical_workflow(
    query="Should we regulate frontier models?",
    use_council=True,
    response_style="json",
)

autocoding_workflow = create_autocoding_workflow(
    requirements="- [ ] Add input validation\n",
    max_turns=3,
)
```
