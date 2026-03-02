"""Tests for the LangGraph continuous dialectical loop."""

from __future__ import annotations

import pytest

from hegelion.langgraph.continuous_dialectic import run_task
from hegelion.langgraph.nodes import (
    DialecticRuntime,
    make_advance_node,
    make_antithesis_node,
    make_critique_node,
    make_execute_node,
    make_human_approval_node,
    make_observe_node,
    make_synthesis_node,
    make_thesis_node,
    make_verify_node,
    route_after_approval,
    route_policy_gate,
)
from hegelion.langgraph.state import (
    DialecticPolicy,
    assess_risk,
    command_is_destructive,
    create_initial_state,
)


def _safe_runtime() -> DialecticRuntime:
    return DialecticRuntime(
        observer=lambda _state: {"workspace_checked": True},
        builder=lambda _state, _prompt: {
            "summary": "Implement feature and run tests",
            "commands": ["pytest -q tests/test_autocoding.py"],
            "target_files": ["hegelion/core/autocoding_state.py"],
            "proposed_patch": "diff --git ...",
        },
        critic=lambda _state, _prompt, _builder: {
            "summary": "No blocking issues.",
            "blocking_issues": [],
        },
        synthesizer=lambda _state, builder, _critic: {
            "kind": "run_commands",
            "commands": builder.get("commands", []),
            "target_files": builder.get("target_files", []),
            "risk_level": "low",
            "rationale": "Apply builder plan.",
        },
        executor=lambda _state, action: {
            "executed": True,
            "commands": action.get("commands", []),
            "target_files": action.get("target_files", []),
        },
        verifier=lambda _state, _exec: {
            "tests_run": ["pytest -q tests/test_autocoding.py"],
            "results": {"pytest -q tests/test_autocoding.py": "passed"},
            "failures": [],
            "passed": True,
            "score": 1.0,
        },
    )


def _risky_runtime(approved: bool) -> DialecticRuntime:
    return DialecticRuntime(
        builder=lambda _state, _prompt: {
            "summary": "Dangerous cleanup",
            "commands": ["rm -rf /tmp/scratch-build"],
            "target_files": [],
        },
        critic=lambda _state, _prompt, _builder: {
            "summary": "Command is high risk; require human approval.",
            "blocking_issues": ["destructive command"],
        },
        synthesizer=lambda _state, builder, critic: {
            "kind": "run_commands",
            "commands": builder.get("commands", []),
            "target_files": [],
            "risk_level": "medium",
            "rationale": critic.get("summary", ""),
        },
        approval=lambda _state, _action: (approved, "Explicit approval callback"),
    )


def test_create_initial_state_embeds_autocoding_session():
    policy = DialecticPolicy(max_turns=5, approval_threshold=0.8)
    state = create_initial_state("Build auth endpoint", "- [ ] Add JWT auth", policy)

    assert state["status"] == "active"
    assert state["phase"] == "observe"
    assert state["max_turns"] == 5
    assert state["autocoding_state"]["phase"] == "player"


def test_destructive_command_detection_and_risk_assessment():
    assert command_is_destructive("rm -rf /tmp/work")
    assert assess_risk(["echo hello"]) == "medium"
    assert assess_risk(["rm -rf /tmp/work"], explicit_risk="low") == "high"


def test_nodes_complete_happy_path_in_one_turn():
    runtime = _safe_runtime()
    policy = DialecticPolicy(max_turns=3, approval_threshold=0.9)
    state = create_initial_state("Ship feature", "- [ ] Implement and test", policy)

    observe = make_observe_node(runtime)
    thesis = make_thesis_node(runtime, policy)
    antithesis = make_antithesis_node(runtime)
    critique = make_critique_node(runtime, policy)
    synthesis = make_synthesis_node(runtime, policy)
    execute = make_execute_node(runtime)
    verify = make_verify_node(runtime)
    advance = make_advance_node(policy)

    state.update(observe(state))
    state.update(thesis(state))
    state.update(critique(state))
    state.update(antithesis(state))
    state.update(synthesis(state))
    assert route_policy_gate(state) == "execute"
    state.update(execute(state))
    state.update(verify(state))
    state.update(advance(state))

    assert state["status"] == "approved"
    assert state["phase"] == "done"
    assert state["turn"] == 1
    assert len(state["history"]) == 1


def test_high_risk_action_routes_to_approval_and_can_continue():
    policy = DialecticPolicy(risk_interrupt_level="high")
    runtime = _risky_runtime(approved=True)
    state = create_initial_state("Cleanup", "- [ ] Remove temp files", policy)

    state.update(make_thesis_node(runtime, policy)(state))
    state.update(make_critique_node(runtime, policy)(state))
    state.update(make_antithesis_node(runtime)(state))
    state.update(make_synthesis_node(runtime, policy)(state))

    assert route_policy_gate(state) == "human_approval"

    state.update(make_human_approval_node(runtime)(state))
    assert state["approval"]["approved"] is True
    assert route_after_approval(state) == "execute"


def test_high_risk_action_can_be_denied():
    policy = DialecticPolicy(risk_interrupt_level="high")
    runtime = _risky_runtime(approved=False)
    state = create_initial_state("Cleanup", "- [ ] Remove temp files", policy)

    state.update(make_thesis_node(runtime, policy)(state))
    state.update(make_critique_node(runtime, policy)(state))
    state.update(make_antithesis_node(runtime)(state))
    state.update(make_synthesis_node(runtime, policy)(state))
    state.update(make_human_approval_node(runtime)(state))

    assert state["status"] == "failed"
    assert state["phase"] == "halt"
    assert route_after_approval(state) == "halt"


def test_run_task_end_to_end_when_langgraph_is_available():
    pytest.importorskip("langgraph")

    runtime = _safe_runtime()
    result = run_task(
        objective="Ship feature",
        requirements="- [ ] Implement and test",
        policy=DialecticPolicy(max_turns=3),
        runtime=runtime,
    )

    assert result["status"] == "approved"
    assert result["phase"] == "done"
    assert result["turn"] == 1
