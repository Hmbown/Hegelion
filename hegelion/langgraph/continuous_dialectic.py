"""LangGraph builder for continuous dialectical coding loops."""

from __future__ import annotations

from typing import Any, Optional

from hegelion.langgraph.nodes import (
    DialecticRuntime,
    done_node,
    halt_node,
    make_advance_node,
    make_antithesis_node,
    make_critique_node,
    make_execute_node,
    make_human_approval_node,
    make_observe_node,
    make_synthesis_node,
    make_thesis_node,
    make_verify_node,
    route_advance,
    route_after_approval,
    route_policy_gate,
)
from hegelion.langgraph.state import DialecticPolicy, create_initial_state


def _load_langgraph_symbols() -> tuple[Any, Any, Any]:
    try:
        from langgraph.graph import END, START, StateGraph  # type: ignore
    except Exception as exc:
        raise ImportError(
            "LangGraph is required for continuous_dialectic. Install with "
            '`pip install "hegelion[langgraph]"` or `pip install langgraph`.'
        ) from exc
    return START, END, StateGraph


def build_dialectic_graph(
    policy: Optional[DialecticPolicy] = None,
    runtime: Optional[DialecticRuntime] = None,
    *,
    checkpointer: Any = None,
) -> Any:
    """Build and compile the continuous dialectical LangGraph."""
    START, END, StateGraph = _load_langgraph_symbols()
    policy = policy or DialecticPolicy()
    runtime = runtime or DialecticRuntime()

    builder = StateGraph(dict)
    builder.add_node("observe", make_observe_node(runtime))
    builder.add_node("thesis", make_thesis_node(runtime, policy))
    builder.add_node("critique", make_critique_node(runtime, policy))
    builder.add_node("antithesis", make_antithesis_node(runtime))
    builder.add_node("synthesis", make_synthesis_node(runtime, policy))
    builder.add_node("policy_gate", lambda state: state)
    builder.add_node("human_approval", make_human_approval_node(runtime))
    builder.add_node("execute", make_execute_node(runtime))
    builder.add_node("verify", make_verify_node(runtime))
    builder.add_node("advance", make_advance_node(policy))
    builder.add_node("done", done_node)
    builder.add_node("halt", halt_node)

    builder.add_edge(START, "observe")
    builder.add_edge("observe", "thesis")
    builder.add_edge("thesis", "critique")
    builder.add_edge("critique", "antithesis")
    builder.add_edge("antithesis", "synthesis")
    builder.add_edge("synthesis", "policy_gate")
    builder.add_conditional_edges(
        "policy_gate",
        route_policy_gate,
        {
            "execute": "execute",
            "human_approval": "human_approval",
        },
    )
    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "execute": "execute",
            "halt": "halt",
        },
    )
    builder.add_edge("execute", "verify")
    builder.add_edge("verify", "advance")
    builder.add_conditional_edges(
        "advance",
        route_advance,
        {
            "thesis": "thesis",
            "done": "done",
            "halt": "halt",
        },
    )
    builder.add_edge("done", END)
    builder.add_edge("halt", END)
    return builder.compile(checkpointer=checkpointer)


def run_task(
    objective: str,
    requirements: str,
    *,
    policy: Optional[DialecticPolicy] = None,
    runtime: Optional[DialecticRuntime] = None,
    task_id: Optional[str] = None,
    session_name: Optional[str] = None,
    thread_id: Optional[str] = None,
    checkpointer: Any = None,
    initial_state_overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Run the graph to completion for a single objective."""
    policy = policy or DialecticPolicy()
    graph = build_dialectic_graph(policy=policy, runtime=runtime, checkpointer=checkpointer)
    state = create_initial_state(
        objective=objective,
        requirements=requirements,
        policy=policy,
        task_id=task_id,
        session_name=session_name,
    )
    if initial_state_overrides:
        state.update(initial_state_overrides)

    config = {"configurable": {"thread_id": thread_id or state["task_id"]}}
    return graph.invoke(state, config=config)
