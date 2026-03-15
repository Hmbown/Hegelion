from __future__ import annotations

import json
import os
from typing import Any

from mcp.server import Server
from mcp.types import CallToolResult, TextContent

from hegelion.core.autocoding_state import AutocodingState, load_session, save_session
from hegelion.core.constants import AutocodingPhase
from hegelion.core.prompt_autocoding import PromptDrivenAutocoding, create_autocoding_workflow
from hegelion.mcp.cli_exec import DEFAULT_TIMEOUT_SECONDS
from hegelion.mcp.constants import (
    AUTOCODE_MODES,
    AUTOCODE_SESSION_ACTIONS,
    AUTOCODE_TURN_ROLES,
    EXECUTION_BACKENDS,
    MCP_SCHEMA_VERSION,
    ToolName,
)
from hegelion.mcp.execution import BackendExecutionError, BackendUnavailableError, execute_prompt
from hegelion.mcp.execution import resolve_requested_backend
from hegelion.mcp.progress import send_progress
from hegelion.mcp.validation import (
    Enum as EnumSpec,
    Int,
    OptStr,
    Str,
    arg_error,
    get_enum_arg,
    get_optional_bool,
    get_optional_int,
    get_optional_str,
    parse_autocoding_state,
    phase_error,
    require_str_arg,
    validated,
)


def _session_label(state: AutocodingState) -> str:
    """Return a human-readable label for the autocoding session."""
    if state.session_name:
        return f"{state.session_name} ({state.session_id[:8]}...)"
    return f"{state.session_id[:8]}..."


def _coach_approved_detected(feedback: str) -> bool:
    normalized = " ".join(feedback.upper().split())
    return "COACH APPROVED" in normalized


def _parse_execution_options(
    name: str,
    arguments: dict[str, Any],
    *,
    role: str,
) -> tuple[bool, str, int, str | None] | CallToolResult:
    execute = get_optional_bool(name, arguments, "execute", False)
    if isinstance(execute, CallToolResult):
        return execute

    try:
        default_backend = resolve_requested_backend(role=role, env=os.environ)
    except ValueError as exc:
        return arg_error(name, f"Error: {exc}", error=str(exc))

    backend = get_enum_arg(name, arguments, "backend", EXECUTION_BACKENDS, default_backend)
    if isinstance(backend, CallToolResult):
        return backend

    timeout_seconds = get_optional_int(
        name, arguments, "timeout_seconds", DEFAULT_TIMEOUT_SECONDS, min_value=1
    )
    if isinstance(timeout_seconds, CallToolResult):
        return timeout_seconds

    cwd = get_optional_str(name, arguments, "cwd")
    if isinstance(cwd, CallToolResult):
        return cwd

    return execute, backend, timeout_seconds, cwd


# ---------------------------------------------------------------------------
# autocode (replaces hegelion + autocoding_init + autocoding_workflow + autocoding_single_shot)
# ---------------------------------------------------------------------------


@validated(
    ToolName.AUTOCODE.value,
    requirements=Str(),
    mode=EnumSpec(allowed=AUTOCODE_MODES, default="workflow"),
    max_turns=Int(default=10, min_value=1),
    session_name=OptStr(),
)
async def handle_autocode(
    app: Server,
    *,
    requirements: str,
    mode: str,
    max_turns: int,
    session_name: str | None,
    _arguments: dict[str, Any],
):
    """Unified autocode handler. Dispatches to mode-specific helpers."""
    name = ToolName.AUTOCODE.value

    if mode == "init":
        return await _autocode_init(app, name, requirements, max_turns, session_name)
    if mode == "workflow":
        return await _autocode_workflow(app, name, requirements, max_turns)
    return await _autocode_single_shot(app, name, requirements, max_turns)


async def _autocode_init(
    app: Server, name: str, requirements: str, max_turns: int, session_name: str | None
):
    """Create a new autocoding session and return its initial state."""
    await send_progress(app, "Initializing autocoding session...", 1.0, 2.0)

    state = AutocodingState.create(
        requirements=requirements,
        max_turns=max_turns,
        session_name=session_name,
    )

    await send_progress(app, "Session initialized", 2.0, 2.0)

    structured = state.to_dict()
    response = f"""# AUTOCODING SESSION INITIALIZED

**Session:** {_session_label(state)}
**Max Turns:** {max_turns}

The session is ready. Next step: call `autocode_turn` with role=player and the returned state.

**Workflow:**
1. Call `autocode_turn` role=player with state -> Execute returned prompt
2. Call `autocode_turn` role=coach with state -> Execute returned prompt
3. Call `autocode_turn` role=advance with coach feedback
4. Repeat until COACH APPROVED or timeout"""

    return ([TextContent(type="text", text=response)], structured)


async def _autocode_workflow(app: Server, name: str, requirements: str, max_turns: int):
    """Generate a structured autocoding workflow recipe as JSON."""
    workflow = create_autocoding_workflow(requirements=requirements, max_turns=max_turns)
    workflow["schema_version"] = MCP_SCHEMA_VERSION

    serialized = json.dumps(workflow, indent=2)
    summary = (
        "Hegelion autocoding workflow ready. Agents should read the structuredContent JSON "
        f"(max_turns={max_turns})."
    )
    contents = [
        TextContent(type="text", text=summary),
        TextContent(type="text", text=serialized),
    ]
    return (contents, workflow)


async def _autocode_single_shot(app: Server, name: str, requirements: str, max_turns: int):
    """Generate a single combined player+coach prompt for one-pass autocoding."""
    await send_progress(app, "Generating single-shot autocoding prompt...", 1.0, 1.0)

    autocoding = PromptDrivenAutocoding()
    prompt_obj = autocoding.generate_single_shot_prompt(
        requirements=requirements,
        max_turns=max_turns,
    )

    structured = {
        "schema_version": MCP_SCHEMA_VERSION,
        **prompt_obj.to_dict(),
        "requirements": requirements,
        "max_turns": max_turns,
    }

    response = f"""# SINGLE-SHOT AUTOCODING PROMPT

{prompt_obj.prompt}

---
**Instructions:** {prompt_obj.instructions}
**Expected Format:** {prompt_obj.expected_format}"""

    return ([TextContent(type="text", text=response)], structured)


# ---------------------------------------------------------------------------
# autocode_turn (replaces player_prompt + coach_prompt + autocoding_advance)
# ---------------------------------------------------------------------------


@validated(
    ToolName.AUTOCODE_TURN.value,
    role=EnumSpec(allowed=AUTOCODE_TURN_ROLES, default="player"),
)
async def handle_autocode_turn(app: Server, *, role: str, _arguments: dict[str, Any]):
    """Unified turn handler. Dispatches by role."""
    name = ToolName.AUTOCODE_TURN.value

    if role == "player":
        return await _turn_player(app, name, _arguments)
    if role == "coach":
        return await _turn_coach(app, name, _arguments)
    return await _turn_advance(app, name, _arguments)


async def _turn_player(app: Server, name: str, arguments: dict[str, Any]):
    """Generate the player implementation prompt and advance state to coach phase."""
    await send_progress(app, "Generating player prompt...", 1.0, 1.0)

    parsed_state = parse_autocoding_state(name, arguments.get("state"))
    if isinstance(parsed_state, CallToolResult):
        return parsed_state
    state = parsed_state

    if state.phase != AutocodingPhase.PLAYER.value:
        return phase_error(
            name,
            expected=AutocodingPhase.PLAYER.value,
            received=state.phase,
            hint=(
                "If you just called autocode (mode=init) or autocode_turn (role=advance), "
                "pass that returned state into autocode_turn role=player."
            ),
        )

    autocoding = PromptDrivenAutocoding()
    prompt_obj = autocoding.generate_player_prompt(
        requirements=state.requirements,
        coach_feedback=state.last_coach_feedback,
        turn_number=state.current_turn + 1,
        max_turns=state.max_turns,
    )

    new_state = state.advance_to_coach()

    structured = {
        "schema_version": MCP_SCHEMA_VERSION,
        **prompt_obj.to_dict(),
        "current_phase": AutocodingPhase.PLAYER.value,
        "next_phase": new_state.phase,
        "state": new_state.to_dict(),
    }

    response = f"""# PLAYER PROMPT (Turn {state.current_turn + 1}/{state.max_turns})

{prompt_obj.prompt}

---
**Instructions:** {prompt_obj.instructions}
**Next Step:** After executing this prompt, call `autocode_turn` role=coach with the updated state."""

    execution_options = _parse_execution_options(name, arguments, role="player")
    if isinstance(execution_options, CallToolResult):
        return execution_options

    execute, backend, timeout_seconds, cwd = execution_options
    if not execute:
        return ([TextContent(type="text", text=response)], structured)

    await send_progress(app, f"Executing player prompt via {backend}...", 1.0, 2.0)
    try:
        execution = await execute_prompt(
            prompt_obj.prompt,
            backend=backend,
            role="player",
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
    except (BackendExecutionError, BackendUnavailableError, ValueError) as exc:
        return arg_error(name, f"Error: {exc}", error=str(exc))

    await send_progress(app, "Player execution result ready", 2.0, 2.0)
    structured.update(execution.to_metadata())
    structured["execute_requested"] = True

    if execution.executed:
        structured["player_output"] = execution.output or ""
        response = f"{response}\n\n---\n**Player Backend Output:**\n{execution.output or ''}"
    else:
        response = (
            f"{response}\n\n---\n**Execution:** "
            f"{execution.execution_skipped_reason or 'Execution skipped'}"
        )

    return ([TextContent(type="text", text=response)], structured)


async def _turn_coach(app: Server, name: str, arguments: dict[str, Any]):
    """Generate the coach verification prompt for the current turn."""
    await send_progress(app, "Generating coach prompt...", 1.0, 1.0)

    parsed_state = parse_autocoding_state(name, arguments.get("state"))
    if isinstance(parsed_state, CallToolResult):
        return parsed_state
    state = parsed_state

    if state.phase != AutocodingPhase.COACH.value:
        return phase_error(
            name,
            expected=AutocodingPhase.COACH.value,
            received=state.phase,
            hint=(
                "Call autocode_turn role=player first; then pass the returned state "
                "(state.phase should be 'coach') into autocode_turn role=coach."
            ),
        )

    autocoding = PromptDrivenAutocoding()
    prompt_obj = autocoding.generate_coach_prompt(
        requirements=state.requirements,
        turn_number=state.current_turn + 1,
        max_turns=state.max_turns,
    )

    structured = {
        "schema_version": MCP_SCHEMA_VERSION,
        **prompt_obj.to_dict(),
        "current_phase": AutocodingPhase.COACH.value,
        "next_phase": state.phase,
        "state": state.to_dict(),
    }

    response = f"""# COACH PROMPT (Turn {state.current_turn + 1}/{state.max_turns})

{prompt_obj.prompt}

---
**Instructions:** {prompt_obj.instructions}
**Next Step:** After executing this prompt, call `autocode_turn` role=advance with the coach's feedback."""

    execution_options = _parse_execution_options(name, arguments, role="coach")
    if isinstance(execution_options, CallToolResult):
        return execution_options

    execute, backend, timeout_seconds, cwd = execution_options
    if not execute:
        return ([TextContent(type="text", text=response)], structured)

    await send_progress(app, f"Executing coach prompt via {backend}...", 1.0, 2.0)
    try:
        execution = await execute_prompt(
            prompt_obj.prompt,
            backend=backend,
            role="coach",
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
    except (BackendExecutionError, BackendUnavailableError, ValueError) as exc:
        return arg_error(name, f"Error: {exc}", error=str(exc))

    await send_progress(app, "Coach execution result ready", 2.0, 2.0)
    structured.update(execution.to_metadata())
    structured["execute_requested"] = True

    coach_feedback = execution.output if execution.executed else None
    structured["coach_feedback"] = coach_feedback
    structured["coach_approved_detected"] = (
        _coach_approved_detected(coach_feedback) if coach_feedback else False
    )

    if execution.executed:
        response = f"{response}\n\n---\n**Independent Coach Output:**\n{coach_feedback or ''}"
    else:
        response = (
            f"{response}\n\n---\n**Execution:** "
            f"{execution.execution_skipped_reason or 'Execution skipped'}"
        )

    return ([TextContent(type="text", text=response)], structured)


async def _turn_advance(app: Server, name: str, arguments: dict[str, Any]):
    """Advance autocoding state after coach review (approve, reject, or timeout)."""
    await send_progress(app, "Advancing autocoding state...", 1.0, 2.0)

    state_dict = arguments.get("state")
    coach_feedback = require_str_arg(name, arguments, "coach_feedback")
    if isinstance(coach_feedback, CallToolResult):
        return coach_feedback
    approved = arguments.get("approved")
    if not isinstance(approved, bool):
        return arg_error(
            name,
            "Error: 'approved' is required and must be a boolean.",
            error="Invalid argument: approved",
            expected="boolean",
            received=approved,
        )

    parsed_state = parse_autocoding_state(name, state_dict)
    if isinstance(parsed_state, CallToolResult):
        return parsed_state
    state = parsed_state

    if state.phase != AutocodingPhase.COACH.value:
        return phase_error(
            name,
            expected=AutocodingPhase.COACH.value,
            received=state.phase,
            hint="Call autocode_turn role=coach first and pass its returned state into role=advance.",
        )

    new_state = state.advance_turn(
        coach_feedback=coach_feedback,
        approved=approved,
    )

    await send_progress(app, "State advanced", 2.0, 2.0)

    structured = new_state.to_dict()

    if new_state.phase == "approved":
        response = f"""# AUTOCODING COMPLETE - APPROVED

**Session:** {new_state.session_id[:8]}...
**Turns Used:** {new_state.current_turn}/{new_state.max_turns}

The implementation has been verified by the coach and meets all requirements."""

    elif new_state.phase == "timeout":
        response = f"""# AUTOCODING COMPLETE - TIMEOUT

**Session:** {new_state.session_id[:8]}...
**Turns Used:** {new_state.current_turn}/{new_state.max_turns}

Maximum turns reached without approval. Review the turn history for progress made."""

    else:
        response = f"""# AUTOCODING - CONTINUING

**Session:** {new_state.session_id[:8]}...
**Turn:** {new_state.current_turn + 1}/{new_state.max_turns}
**Phase:** {new_state.phase}

**Next Step:** Call `autocode_turn` role=player with the updated state to continue implementation."""

    return ([TextContent(type="text", text=response)], structured)


# ---------------------------------------------------------------------------
# autocode_session (replaces autocoding_save + autocoding_load)
# ---------------------------------------------------------------------------


@validated(
    ToolName.AUTOCODE_SESSION.value,
    action=EnumSpec(allowed=AUTOCODE_SESSION_ACTIONS, default="save"),
)
async def handle_autocode_session(app: Server, *, action: str, _arguments: dict[str, Any]):
    """Unified session handler. Dispatches by action."""
    name = ToolName.AUTOCODE_SESSION.value

    if action == "save":
        return await _session_save(app, name, _arguments)
    return await _session_load(app, name, _arguments)


async def _session_save(app: Server, name: str, arguments: dict[str, Any]):
    """Persist autocoding session state to a JSON file."""
    state_dict = arguments.get("state")
    filepath = require_str_arg(name, arguments, "filepath")
    if isinstance(filepath, CallToolResult):
        return filepath

    parsed_state = parse_autocoding_state(name, state_dict)
    if isinstance(parsed_state, CallToolResult):
        return parsed_state
    state = parsed_state
    save_session(state, filepath)

    structured = {
        "schema_version": MCP_SCHEMA_VERSION,
        "session_id": state.session_id,
        "filepath": filepath,
        "saved": True,
    }
    response = f"""# SESSION SAVED

**Session ID:** {state.session_id[:8]}...
**Saved to:** {filepath}
**Phase:** {state.phase}
**Turn:** {state.current_turn + 1}/{state.max_turns}

Session saved successfully. Use `autocode_session` action=load with the filepath to restore."""

    return ([TextContent(type="text", text=response)], structured)


async def _session_load(app: Server, name: str, arguments: dict[str, Any]):
    """Restore autocoding session state from a JSON file."""
    filepath = require_str_arg(name, arguments, "filepath")
    if isinstance(filepath, CallToolResult):
        return filepath

    try:
        state = load_session(filepath)
    except FileNotFoundError:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Session file not found: {filepath}")],
            structuredContent={
                "schema_version": MCP_SCHEMA_VERSION,
                "error": f"File not found: {filepath}",
            },
            isError=True,
        )
    except json.JSONDecodeError as exc:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Invalid JSON in session file: {exc}")],
            structuredContent={
                "schema_version": MCP_SCHEMA_VERSION,
                "error": f"Invalid JSON: {str(exc)}",
            },
            isError=True,
        )

    structured = state.to_dict()
    response = f"""# SESSION LOADED

**Session ID:** {state.session_id[:8]}...
**Loaded from:** {filepath}
**Phase:** {state.phase}
**Turn:** {state.current_turn + 1}/{state.max_turns}

Session restored. Continue with `autocode_turn` based on phase:
- If phase is "player": call `autocode_turn` role=player
- If phase is "coach": call `autocode_turn` role=coach"""

    return ([TextContent(type="text", text=response)], structured)
