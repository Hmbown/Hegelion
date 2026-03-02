# Python API

Hegelion's Python API is prompt-driven. It **does not call an LLM for you**; it generates structured prompts you run with your model of choice.

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

## Continuous LangGraph Loop (Builder → Critic → Synthesis)

If you want a durable, cyclic coding agent with policy gates and optional
human approval, use `hegelion.langgraph`.

Graph shape:
`observe -> thesis -> critique -> antithesis -> synthesis -> (stop|continue)` with
execute/verify steps on the continue path.

```python
from hegelion.langgraph import DialecticPolicy, DialecticRuntime, run_task

runtime = DialecticRuntime(
    builder=lambda state, prompt: {
        "summary": "Implement requirement and run targeted tests",
        "commands": ["uv run pytest -q tests/test_autocoding.py"],
        "target_files": ["hegelion/core/autocoding_state.py"],
    },
    critic=lambda state, prompt, builder: {
        "summary": "Check missing tests and risky assumptions",
        "blocking_issues": [],
    },
    synthesizer=lambda state, builder, critic: {
        "kind": "run_commands",
        "commands": builder["commands"],
        "target_files": builder["target_files"],
        "risk_level": "low",
        "rationale": "Synthesis accepts builder plan after critique.",
    },
    executor=lambda state, action: {"executed": True, "commands": action["commands"]},
    verifier=lambda state, execution: {
        "tests_run": action["commands"] if (action := execution) else [],
        "results": {},
        "failures": [],
        "passed": True,
        "score": 1.0,
    },
)

result = run_task(
    objective="Implement the requirement checklist",
    requirements="- [ ] Add endpoint\n- [ ] Add tests\n",
    policy=DialecticPolicy(max_turns=6, approval_threshold=0.9),
    runtime=runtime,
)

print(result["status"])  # approved | timeout | failed
```

Installation for this feature set:

```bash
pip install "hegelion[langgraph]"
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
