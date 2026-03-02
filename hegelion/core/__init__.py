"""Hegelion core: pure prompt generation and state management."""

from hegelion.core.autocoding_state import AutocodingState, load_session, save_session
from hegelion.core.constants import AutocodingPhase, DialecticPhase
from hegelion.core.prompt_autocoding import (
    AutocodingPrompt,
    PromptDrivenAutocoding,
    create_autocoding_workflow,
)
from hegelion.core.prompt_dialectic import (
    DialecticalPrompt,
    PromptDrivenDialectic,
    create_dialectical_workflow,
    create_single_shot_dialectic_prompt,
)

__all__ = [
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
    "AutocodingState",
    "PromptDrivenAutocoding",
    "create_autocoding_workflow",
    # Session persistence
    "load_session",
    "save_session",
]
