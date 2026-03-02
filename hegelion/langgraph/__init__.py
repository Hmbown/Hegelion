"""LangGraph orchestration helpers for continuous dialectical autocoding.

This package provides a guarded builder/critic/synthesis loop that can run on
LangGraph's cyclical state graph runtime.
"""

from hegelion.langgraph.continuous_dialectic import build_dialectic_graph, run_task
from hegelion.langgraph.nodes import DialecticRuntime
from hegelion.langgraph.state import DialecticPolicy, create_initial_state

__all__ = [
    "DialecticPolicy",
    "DialecticRuntime",
    "build_dialectic_graph",
    "create_initial_state",
    "run_task",
]
