"""
Hegelion: Dialectical Reasoning Harness for LLMs

A Python package that generates structured thesis-antithesis-synthesis responses
using Large Language Models, making reasoning patterns and contradictions explicit.
"""

__version__ = "0.5.0"
__author__ = "Hegelion Contributors"

from hegelion.core.constants import AutocodingPhase, DialecticPhase
from hegelion.core.prompt_dialectic import (
    DialecticalPrompt,
    PromptDrivenDialectic,
    create_dialectical_workflow,
    create_single_shot_dialectic_prompt,
)
from hegelion.core.prompt_autocoding import (
    AutocodingPrompt,
    PromptDrivenAutocoding,
    create_autocoding_workflow,
)
from hegelion.core.autocoding_state import AutocodingState

__all__ = [
    "__version__",
    # Enums
    "AutocodingPhase",
    "DialecticPhase",
    # Dialectical reasoning
    "DialecticalPrompt",
    "PromptDrivenDialectic",
    "create_dialectical_workflow",
    "create_single_shot_dialectic_prompt",
    # Autocoding
    "AutocodingPrompt",
    "PromptDrivenAutocoding",
    "create_autocoding_workflow",
    "AutocodingState",
]
