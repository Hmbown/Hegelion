from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import CallToolResult, TextContent

from hegelion.core.prompt_dialectic import PromptDrivenDialectic
from hegelion.core.prompt_dialectic import create_dialectical_workflow
from hegelion.core.prompt_dialectic import create_single_shot_dialectic_prompt
from hegelion.mcp.cli_exec import DEFAULT_TIMEOUT_SECONDS, auto_execute_enabled, load_llm_command
from hegelion.mcp.cli_exec import run_llm_command, validate_llm_output
from hegelion.mcp.constants import (
    DIALECTIC_MODES,
    MCP_SCHEMA_VERSION,
    RESPONSE_STYLES,
    ToolName,
    WORKFLOW_FORMATS,
)
from hegelion.mcp.progress import send_progress
from hegelion.mcp.response import (
    DIALECTIC_PHASE_SCHEMAS,
    phase_schema_for_style,
    response_schema_for_style,
    response_style_summary,
)
from hegelion.mcp.validation import (
    Enum as EnumSpec,
    Str,
    arg_error,
    get_enum_arg,
    get_optional_bool,
    get_optional_int,
    require_str_arg,
    validated,
)


def _prompt_structured(prompt_obj: Any, response_style: str) -> dict[str, Any]:
    structured = {
        "schema_version": MCP_SCHEMA_VERSION,
        "phase": prompt_obj.phase,
        "prompt": prompt_obj.prompt,
        "instructions": prompt_obj.instructions,
        "expected_format": prompt_obj.expected_format,
        "response_style": response_style,
    }
    response_schema = phase_schema_for_style(response_style, prompt_obj.phase)
    if response_schema:
        structured["response_schema"] = response_schema
    return structured


def _render_prompt_response(title: str, prompt_obj: Any) -> str:
    return f"""# {title}

{prompt_obj.prompt}

**Instructions:** {prompt_obj.instructions}
**Expected Format:** {prompt_obj.expected_format}"""


@validated(
    ToolName.DIALECTIC.value,
    query=Str(),
    mode=EnumSpec(allowed=DIALECTIC_MODES, default="single_shot"),
)
async def handle_dialectic(app: Server, *, query: str, mode: str, _arguments: dict[str, Any]):
    """Unified dialectic handler. Dispatches to mode-specific helpers."""
    name = ToolName.DIALECTIC.value

    if mode == "workflow":
        return await _handle_workflow(app, name, query, _arguments)
    if mode == "single_shot":
        return await _handle_single_shot(app, name, query, _arguments)
    if mode == "thesis":
        return await _handle_thesis(app, name, query, _arguments)
    if mode == "antithesis":
        return await _handle_antithesis(app, name, query, _arguments)
    if mode == "synthesis":
        return await _handle_synthesis(app, name, query, _arguments)


async def _handle_workflow(app: Server, name: str, query: str, arguments: dict[str, Any]):
    use_search = get_optional_bool(name, arguments, "use_search", False)
    if isinstance(use_search, CallToolResult):
        return use_search
    use_council = get_optional_bool(name, arguments, "use_council", False)
    if isinstance(use_council, CallToolResult):
        return use_council
    format_type = get_enum_arg(name, arguments, "format", WORKFLOW_FORMATS, "workflow")
    if isinstance(format_type, CallToolResult):
        return format_type
    response_style = get_enum_arg(name, arguments, "response_style", RESPONSE_STYLES, "sections")
    if isinstance(response_style, CallToolResult):
        return response_style

    await send_progress(app, "━━━ Preparing dialectical workflow ━━━", 1.0)

    if format_type == "single_prompt":
        await send_progress(app, "━━━ Generating single-shot prompt ━━━", 2.0)
        prompt = create_single_shot_dialectic_prompt(
            query=query,
            use_search=use_search,
            use_council=use_council,
            response_style=response_style,
        )
        await send_progress(app, "━━━ Prompt ready ━━━", 3.0)
        structured = {
            "schema_version": MCP_SCHEMA_VERSION,
            "query": query,
            "format": "single_prompt",
            "use_search": use_search,
            "use_council": use_council,
            "response_style": response_style,
            "prompt": prompt,
        }
        response_schema = response_schema_for_style(response_style)
        if response_schema:
            structured["response_schema"] = response_schema
        return ([TextContent(type="text", text=prompt)], structured)

    await send_progress(app, "━━━ THESIS prompt ready ━━━", 1.0)
    await send_progress(app, "━━━ ANTITHESIS prompt ready ━━━", 2.0)
    await send_progress(app, "━━━ SYNTHESIS prompt ready ━━━", 3.0)
    workflow = create_dialectical_workflow(
        query=query,
        use_search=use_search,
        use_council=use_council,
        response_style=response_style,
    )
    workflow["schema_version"] = MCP_SCHEMA_VERSION
    workflow.setdefault("instructions", {})
    workflow["instructions"]["response_style"] = response_style
    workflow["instructions"]["response_style_note"] = response_style_summary(response_style)
    response_schema = response_schema_for_style(response_style)
    if response_schema:
        workflow["instructions"]["response_schema"] = response_schema
        workflow["instructions"]["phase_schemas"] = DIALECTIC_PHASE_SCHEMAS

    serialized = json.dumps(workflow, indent=2)
    summary = (
        "Hegelion dialectical workflow ready. Agents should read the structuredContent JSON. "
        f"Human-readable summary: query='{query}', response_style='{response_style}'."
    )
    contents = [
        TextContent(type="text", text=summary),
        TextContent(type="text", text=serialized),
    ]
    return (contents, workflow)


async def _handle_single_shot(app: Server, name: str, query: str, arguments: dict[str, Any]):
    use_search = get_optional_bool(name, arguments, "use_search", False)
    if isinstance(use_search, CallToolResult):
        return use_search
    use_council = get_optional_bool(name, arguments, "use_council", False)
    if isinstance(use_council, CallToolResult):
        return use_council
    response_style = get_enum_arg(name, arguments, "response_style", RESPONSE_STYLES, "sections")
    if isinstance(response_style, CallToolResult):
        return response_style

    execute = get_optional_bool(name, arguments, "execute", auto_execute_enabled())
    if isinstance(execute, CallToolResult):
        return execute
    timeout_seconds = get_optional_int(
        name, arguments, "timeout_seconds", DEFAULT_TIMEOUT_SECONDS, min_value=1
    )
    if isinstance(timeout_seconds, CallToolResult):
        return timeout_seconds
    max_retries = get_optional_int(name, arguments, "max_retries", 0, min_value=0)
    if isinstance(max_retries, CallToolResult):
        return max_retries

    prompt = create_single_shot_dialectic_prompt(
        query=query,
        use_search=use_search,
        use_council=use_council,
        response_style=response_style,
    )

    structured = {
        "schema_version": MCP_SCHEMA_VERSION,
        "query": query,
        "use_search": use_search,
        "use_council": use_council,
        "response_style": response_style,
        "prompt": prompt,
        "mode": "prompt",
    }
    response_schema = response_schema_for_style(response_style)
    if response_schema:
        structured["response_schema"] = response_schema
    note = response_style_summary(response_style)

    if not execute:
        contents = [TextContent(type="text", text=f"{note}\n\n{prompt}")]
        return (contents, structured)

    command = None
    try:
        command = load_llm_command()
    except (json.JSONDecodeError, ValueError) as exc:
        return arg_error(
            name,
            f"Error: Invalid LLM CLI configuration: {exc}",
            error=f"Invalid LLM CLI configuration: {exc}",
        )

    if not command:
        return arg_error(
            name,
            "Error: Execution requested but no LLM CLI command configured. "
            "Set HEGELION_LLM_COMMAND_JSON or HEGELION_LLM_COMMAND.",
            error="Missing LLM CLI command",
            expected="HEGELION_LLM_COMMAND_JSON or HEGELION_LLM_COMMAND",
            received=None,
        )

    await send_progress(app, "━━━ Executing dialectic via CLI ━━━", 1.0, 2.0)

    attempts = 0
    last_stdout = ""
    last_stderr = ""
    last_returncode = 0
    last_validation_error: str | None = None
    attempt_prompt = prompt

    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        if max_retries:
            await send_progress(
                app,
                f"━━━ CLI attempt {attempts}/{max_retries + 1} ━━━",
                1.0 + (attempts / (max_retries + 1)),
                2.0,
            )

        try:
            stdout, stderr, returncode = await run_llm_command(
                command, attempt_prompt, timeout_seconds=timeout_seconds
            )
        except (FileNotFoundError, TimeoutError) as exc:
            return arg_error(name, f"Error: {exc}", error=str(exc))

        last_stdout, last_stderr, last_returncode = stdout, stderr, returncode
        if returncode != 0:
            return arg_error(
                name,
                f"Error: LLM CLI exited with code {returncode}.\n\nstderr:\n{stderr.strip()}",
                error="LLM CLI failed",
                expected="return code 0",
                received=returncode,
            )

        output = stdout.strip()
        valid, validation_error = validate_llm_output(output, response_style)
        if valid:
            last_validation_error = None
            break

        last_validation_error = validation_error or "Validation failed"
        attempt_prompt = (
            f"{prompt}\n\nIMPORTANT: Your last response did not match the required format "
            f"({last_validation_error}). Re-run and strictly follow the output format instructions. "
            "Output only the final answer."
        )

    await send_progress(app, "━━━ CLI result ready ━━━", 2.0, 2.0)

    output_text = last_stdout.strip()
    structured.update(
        {
            "mode": "executed",
            "execute": True,
            "llm_cli": command[0],
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "attempts": attempts,
            "returncode": last_returncode,
            "output": output_text,
        }
    )
    if last_stderr.strip():
        structured["stderr"] = last_stderr.strip()
    if last_validation_error:
        structured["validation_error"] = last_validation_error

    return ([TextContent(type="text", text=output_text)], structured)


async def _handle_thesis(app: Server, name: str, query: str, arguments: dict[str, Any]):
    await send_progress(app, "━━━ THESIS ━━━ Generating prompt...", 1.0, 1.0)
    response_style = get_enum_arg(name, arguments, "response_style", RESPONSE_STYLES, "sections")
    if isinstance(response_style, CallToolResult):
        return response_style

    dialectic = PromptDrivenDialectic()
    prompt_obj = dialectic.generate_thesis_prompt(query, response_style=response_style)

    structured = _prompt_structured(prompt_obj, response_style)
    response = _render_prompt_response("THESIS PROMPT", prompt_obj)

    return ([TextContent(type="text", text=response)], structured)


async def _handle_antithesis(app: Server, name: str, query: str, arguments: dict[str, Any]):
    await send_progress(app, "━━━ ANTITHESIS ━━━ Generating prompt...", 1.0, 1.0)
    thesis = require_str_arg(name, arguments, "thesis")
    if isinstance(thesis, CallToolResult):
        return thesis
    use_search = get_optional_bool(name, arguments, "use_search", False)
    if isinstance(use_search, CallToolResult):
        return use_search
    use_council = get_optional_bool(name, arguments, "use_council", False)
    if isinstance(use_council, CallToolResult):
        return use_council
    response_style = get_enum_arg(name, arguments, "response_style", RESPONSE_STYLES, "sections")
    if isinstance(response_style, CallToolResult):
        return response_style

    dialectic = PromptDrivenDialectic()

    if use_council:
        council_prompts = dialectic.generate_council_prompts(
            query, thesis, response_style=response_style
        )
        response_parts = ["# COUNCIL ANTITHESIS PROMPTS\n"]
        structured_prompts = []

        for prompt_obj in council_prompts:
            response_parts.append(f"## {prompt_obj.phase.replace('_', ' ').title()}")
            response_parts.append(prompt_obj.prompt)
            response_parts.append(f"**Instructions:** {prompt_obj.instructions}")
            response_parts.append("")
            structured_prompts.append(_prompt_structured(prompt_obj, response_style))

        structured = {
            "schema_version": MCP_SCHEMA_VERSION,
            "prompts": structured_prompts,
            "phase": "antithesis_council",
            "response_style": response_style,
        }
        response = "\n".join(response_parts)
    else:
        prompt_obj = dialectic.generate_antithesis_prompt(
            query, thesis, use_search, response_style=response_style
        )
        structured = _prompt_structured(prompt_obj, response_style)
        response = _render_prompt_response("ANTITHESIS PROMPT", prompt_obj)

    return ([TextContent(type="text", text=response)], structured)


async def _handle_synthesis(app: Server, name: str, query: str, arguments: dict[str, Any]):
    await send_progress(app, "━━━ SYNTHESIS ━━━ Generating prompt...", 1.0, 1.0)
    thesis = require_str_arg(name, arguments, "thesis")
    if isinstance(thesis, CallToolResult):
        return thesis
    antithesis = require_str_arg(name, arguments, "antithesis")
    if isinstance(antithesis, CallToolResult):
        return antithesis
    response_style = get_enum_arg(name, arguments, "response_style", RESPONSE_STYLES, "sections")
    if isinstance(response_style, CallToolResult):
        return response_style

    dialectic = PromptDrivenDialectic()
    prompt_obj = dialectic.generate_synthesis_prompt(
        query, thesis, antithesis, response_style=response_style
    )

    structured = _prompt_structured(prompt_obj, response_style)
    response = _render_prompt_response("SYNTHESIS PROMPT", prompt_obj)

    return ([TextContent(type="text", text=response)], structured)
