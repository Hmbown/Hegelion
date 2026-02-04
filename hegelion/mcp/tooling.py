from __future__ import annotations

from mcp.types import Tool

from hegelion.mcp.constants import AUTOCODING_SKILL_MODES, RESPONSE_STYLE_ENUM, ToolName


def build_tools() -> list[Tool]:
    """Return dialectical reasoning tools that work with any LLM."""
    response_style_enum = list(RESPONSE_STYLE_ENUM)
    tools = [
        Tool(
            name=ToolName.DIALECTICAL_WORKFLOW.value,
            description=(
                "Step-by-step prompts for dialectical reasoning (thesis → antithesis → synthesis). "
                "Set response_style to control output: 'json' (structured, agent-friendly), "
                "'sections' (full text), or 'synthesis_only' (just the resolution). "
                "Example: {'query': 'Should AI be regulated?', 'response_style': 'json'}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to analyze dialectically",
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
                    "use_judge": {
                        "type": "boolean",
                        "description": "Include quality evaluation step",
                        "default": False,
                    },
                    "format": {
                        "type": "string",
                        "enum": ["workflow", "single_prompt"],
                        "description": "Return structured workflow or single comprehensive prompt",
                        "default": "workflow",
                    },
                    "response_style": {
                        "type": "string",
                        "enum": response_style_enum,
                        "description": (
                            "Shape of the final output you want from the LLM: full thesis/antithesis/synthesis sections,"
                            " synthesis-only, or JSON with all fields."
                        ),
                        "default": "sections",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name=ToolName.DIALECTICAL_SINGLE_SHOT.value,
            description=(
                "One comprehensive prompt that makes the LLM do thesis → antithesis → synthesis in one go. "
                "Use response_style: 'json' (structured), 'sections' (full text), or 'synthesis_only' (just the resolution)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to analyze dialectically",
                    },
                    "use_search": {
                        "type": "boolean",
                        "description": "Include instructions to use search tools",
                        "default": False,
                    },
                    "use_council": {
                        "type": "boolean",
                        "description": "Enable multi-perspective council critiques",
                        "default": False,
                    },
                    "response_style": {
                        "type": "string",
                        "enum": response_style_enum,
                        "description": (
                            "Format you want the model to return: full sections, synthesis-only, or JSON with thesis/antithesis/synthesis."
                        ),
                        "default": "sections",
                    },
                    "execute": {
                        "type": "boolean",
                        "description": (
                            "If true, run the generated prompt through a configured LLM CLI "
                            "(HEGELION_LLM_COMMAND_JSON or HEGELION_LLM_COMMAND) and return the model output."
                        ),
                        "default": False,
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": (
                            "Timeout (seconds) for the LLM CLI call when execute=true (default: 120)."
                        ),
                        "default": 120,
                    },
                    "max_retries": {
                        "type": "integer",
                        "description": (
                            "Best-effort retries if output fails basic format validation when execute=true "
                            "(default: 0)."
                        ),
                        "default": 0,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name=ToolName.THESIS_PROMPT.value,
            description=(
                "Generate just the thesis prompt for dialectical reasoning. "
                "Use this when you want to execute dialectical reasoning step-by-step."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to analyze dialectically",
                    },
                    "response_style": {
                        "type": "string",
                        "enum": response_style_enum,
                        "description": "Optional response formatting guidance for the thesis output",
                        "default": "sections",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name=ToolName.ANTITHESIS_PROMPT.value,
            description=(
                "Generate the antithesis prompt for dialectical reasoning. "
                "Requires the thesis output from a previous step."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The original question or topic",
                    },
                    "thesis": {
                        "type": "string",
                        "description": "The thesis output to critique",
                    },
                    "use_search": {
                        "type": "boolean",
                        "description": "Include instructions to use search tools",
                        "default": False,
                    },
                    "use_council": {
                        "type": "boolean",
                        "description": "Use council-based multi-perspective critique",
                        "default": False,
                    },
                    "response_style": {
                        "type": "string",
                        "enum": response_style_enum,
                        "description": "Optional response formatting guidance for the antithesis output",
                        "default": "sections",
                    },
                },
                "required": ["query", "thesis"],
            },
        ),
        Tool(
            name=ToolName.SYNTHESIS_PROMPT.value,
            description=(
                "Generate the synthesis prompt for dialectical reasoning. "
                "Requires thesis and antithesis outputs from previous steps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The original question or topic",
                    },
                    "thesis": {
                        "type": "string",
                        "description": "The thesis output",
                    },
                    "antithesis": {
                        "type": "string",
                        "description": "The antithesis critique output",
                    },
                    "response_style": {
                        "type": "string",
                        "enum": response_style_enum,
                        "description": "Optional response formatting guidance for the synthesis output",
                        "default": "sections",
                    },
                },
                "required": ["query", "thesis", "antithesis"],
            },
        ),
        # === AUTOCODING TOOLS (based on g3 paper) ===
        Tool(
            name=ToolName.HEGELION.value,
            description=(
                "Brand-first autocoding entrypoint. "
                "Use mode=workflow for a step-by-step recipe, mode=single_shot for a single prompt, "
                "or mode=init to create a session state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "The requirements document (source of truth). Should be structured as a checklist.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": sorted(AUTOCODING_SKILL_MODES),
                        "description": "Autocoding entrypoint mode",
                        "default": "workflow",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum turns before timeout (default: 10)",
                        "default": 10,
                    },
                    "approval_threshold": {
                        "type": "number",
                        "description": "Minimum compliance score for approval (0-1, default: 0.9)",
                        "default": 0.9,
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Optional human-readable session name (e.g., 'auth-feature')",
                    },
                },
                "required": ["requirements"],
            },
        ),
        Tool(
            name=ToolName.AUTOCODING_INIT.value,
            description=(
                "Initialize a dialectical autocoding session with requirements. "
                "Returns session state to pass to subsequent tool calls. "
                "Based on the g3 paper's coach-player adversarial cooperation paradigm."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "The requirements document (source of truth). Should be structured as a checklist.",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum turns before timeout (default: 10)",
                        "default": 10,
                    },
                    "approval_threshold": {
                        "type": "number",
                        "description": "Minimum compliance score for approval (0-1, default: 0.9)",
                        "default": 0.9,
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Optional human-readable session name (e.g., 'auth-feature')",
                    },
                },
                "required": ["requirements"],
            },
        ),
        Tool(
            name=ToolName.AUTOCODING_WORKFLOW.value,
            description=(
                "Return a structured autocoding workflow (player/coach loop) for orchestration. "
                "Useful for agents that want a step-by-step recipe before running the tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "The requirements document (source of truth)",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum turns before timeout (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["requirements"],
            },
        ),
        Tool(
            name=ToolName.PLAYER_PROMPT.value,
            description=(
                "Generate the implementation prompt for the player agent in autocoding. "
                "The player focuses on implementing requirements, NOT declaring success. "
                "Returns an updated state advanced to coach phase for the next call."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "object",
                        "description": "AutocodingState dict from autocoding_init or autocoding_advance",
                    },
                },
                "required": ["state"],
            },
        ),
        Tool(
            name=ToolName.COACH_PROMPT.value,
            description=(
                "Generate the validation prompt for the coach agent in autocoding. "
                "The coach verifies implementation against requirements, ignoring player's self-assessment. "
                "Requires state.phase=='coach'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "object",
                        "description": "AutocodingState dict from player phase",
                    },
                },
                "required": ["state"],
            },
        ),
        Tool(
            name=ToolName.AUTOCODING_ADVANCE.value,
            description=(
                "Advance autocoding state after coach review. "
                "Updates turn count, records feedback, and determines next phase."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "object",
                        "description": "AutocodingState dict from coach phase",
                    },
                    "coach_feedback": {
                        "type": "string",
                        "description": "The coach's feedback text (compliance checklist and actions needed)",
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "Whether the coach approved the implementation (look for 'COACH APPROVED')",
                    },
                    "compliance_score": {
                        "type": "number",
                        "description": "Optional compliance score (0-1) based on checklist items satisfied",
                    },
                },
                "required": ["state", "coach_feedback", "approved"],
            },
        ),
        Tool(
            name=ToolName.AUTOCODING_SINGLE_SHOT.value,
            description=(
                "Single comprehensive prompt for self-directed autocoding. "
                "Combines player and coach roles with iterative implementation and self-verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "The requirements document (source of truth)",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum iterations to attempt (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["requirements"],
            },
        ),
        Tool(
            name=ToolName.AUTOCODING_SAVE.value,
            description=(
                "Save an autocoding session to a JSON file. "
                "Use this to persist session state for later resumption."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "object",
                        "description": "AutocodingState dict to save",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to save the session JSON file",
                    },
                },
                "required": ["state", "filepath"],
            },
        ),
        Tool(
            name=ToolName.AUTOCODING_LOAD.value,
            description=(
                "Load an autocoding session from a JSON file. "
                "Use this to resume a previously saved session."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the session JSON file to load",
                    },
                },
                "required": ["filepath"],
            },
        ),
    ]
    return tools
