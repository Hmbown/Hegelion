from __future__ import annotations

from mcp.types import Tool

from hegelion.mcp.constants import (
    AUTOCODE_MODES_ENUM,
    AUTOCODE_SESSION_ACTIONS_ENUM,
    AUTOCODE_TURN_ROLES_ENUM,
    DIALECTIC_MODES_ENUM,
    EXECUTION_BACKEND_ENUM,
    RESPONSE_STYLE_ENUM,
    ToolName,
)


def build_tools() -> list[Tool]:
    """Return dialectical reasoning tools that work with any LLM."""
    response_style_enum = list(RESPONSE_STYLE_ENUM)
    tools = [
        # === DIALECTIC (unified) ===
        Tool(
            name=ToolName.DIALECTIC.value,
            description=(
                "Dialectical reasoning (thesis → antithesis → synthesis). "
                "Modes: single_shot (one prompt), workflow (step-by-step recipe), "
                "thesis/antithesis/synthesis (individual phase prompts). "
                "Use response_style to control output: 'json', 'sections', or 'synthesis_only'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to analyze dialectically",
                    },
                    "mode": {
                        "type": "string",
                        "enum": list(DIALECTIC_MODES_ENUM),
                        "description": (
                            "single_shot: one comprehensive prompt. "
                            "workflow: structured step-by-step recipe. "
                            "thesis/antithesis/synthesis: individual phase prompts."
                        ),
                        "default": "single_shot",
                    },
                    "thesis": {
                        "type": "string",
                        "description": "Thesis text (required for antithesis/synthesis modes)",
                    },
                    "antithesis": {
                        "type": "string",
                        "description": "Antithesis text (required for synthesis mode)",
                    },
                    "use_search": {
                        "type": "boolean",
                        "description": "Include instructions to use search tools for real-world grounding",
                        "default": False,
                    },
                    "use_council": {
                        "type": "boolean",
                        "description": "Enable multi-perspective council critiques (Logician, Empiricist, Ethicist)",
                        "default": False,
                    },
                    "response_style": {
                        "type": "string",
                        "enum": response_style_enum,
                        "description": (
                            "Shape of the final output: 'sections' (full text), "
                            "'synthesis_only' (just the resolution), or 'json' (structured)."
                        ),
                        "default": "sections",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["workflow", "single_prompt"],
                        "description": "For workflow mode: return structured workflow or single prompt",
                        "default": "workflow",
                    },
                    "execute": {
                        "type": "boolean",
                        "description": (
                            "If true and mode=single_shot, run the prompt through the selected backend "
                            "and return model output when execution succeeds."
                        ),
                        "default": False,
                    },
                    "backend": {
                        "type": "string",
                        "enum": list(EXECUTION_BACKEND_ENUM),
                        "description": (
                            "Execution backend when execute=true. "
                            "auto prefers Codex MCP, then CLI, then prompt-only fallback."
                        ),
                        "default": "auto",
                    },
                    "cwd": {
                        "type": "string",
                        "description": (
                            "Optional working directory for backend execution. "
                            "Defaults to the MCP server process cwd."
                        ),
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": (
                            "Timeout (seconds) for backend execution when execute=true (default: 120)"
                        ),
                        "default": 120,
                    },
                    "max_retries": {
                        "type": "integer",
                        "description": (
                            "Retries if output fails format validation when execute=true (default: 0)"
                        ),
                        "default": 0,
                    },
                },
                "required": ["query"],
            },
        ),
        # === AUTOCODE (replaces hegelion + autocoding_init/workflow/single_shot) ===
        Tool(
            name=ToolName.AUTOCODE.value,
            description=(
                "Start autocoding (g3 coach-player paradigm). "
                "mode=init: create session state. "
                "mode=workflow: step-by-step recipe. "
                "mode=single_shot: one comprehensive prompt."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "The requirements document (source of truth). Structured as a checklist.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": list(AUTOCODE_MODES_ENUM),
                        "description": "init: create session state. workflow: step-by-step recipe. single_shot: one prompt.",
                        "default": "workflow",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum turns before timeout (default: 10)",
                        "default": 10,
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Optional human-readable session name (e.g., 'auth-feature')",
                    },
                },
                "required": ["requirements"],
            },
        ),
        # === AUTOCODE_TURN (replaces player_prompt + coach_prompt + autocoding_advance) ===
        Tool(
            name=ToolName.AUTOCODE_TURN.value,
            description=(
                "Execute one step in the autocoding loop. "
                "role=player: generate implementation prompt (advances state to coach). "
                "role=coach: generate verification prompt. "
                "role=advance: advance state after coach review."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": list(AUTOCODE_TURN_ROLES_ENUM),
                        "description": "Which step to execute: player, coach, or advance",
                    },
                    "state": {
                        "type": "object",
                        "description": "AutocodingState dict from previous step",
                    },
                    "coach_feedback": {
                        "type": "string",
                        "description": "Coach feedback text (required for role=advance)",
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "Whether coach approved (required for role=advance)",
                    },
                    "execute": {
                        "type": "boolean",
                        "description": (
                            "If true for role=player or role=coach, execute the returned prompt through "
                            "the selected backend."
                        ),
                        "default": False,
                    },
                    "backend": {
                        "type": "string",
                        "enum": list(EXECUTION_BACKEND_ENUM),
                        "description": (
                            "Execution backend for role=player or role=coach. "
                            "auto prefers Codex MCP, then CLI, then prompt-only fallback."
                        ),
                        "default": "auto",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": (
                            "Timeout (seconds) for backend execution when execute=true (default: 120)"
                        ),
                        "default": 120,
                    },
                    "cwd": {
                        "type": "string",
                        "description": (
                            "Optional working directory for backend execution. "
                            "Defaults to the MCP server process cwd."
                        ),
                    },
                },
                "required": ["role", "state"],
            },
        ),
        # === AUTOCODE_SESSION (replaces autocoding_save + autocoding_load) ===
        Tool(
            name=ToolName.AUTOCODE_SESSION.value,
            description=(
                "Save or load an autocoding session. "
                "action=save: persist state to file. "
                "action=load: restore state from file."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": list(AUTOCODE_SESSION_ACTIONS_ENUM),
                        "description": "save: persist state. load: restore state.",
                    },
                    "state": {
                        "type": "object",
                        "description": "AutocodingState dict to save (required for action=save)",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path for session JSON file",
                    },
                },
                "required": ["action", "filepath"],
            },
        ),
    ]
    return tools
