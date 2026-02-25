"""Model-agnostic MCP server for dialectical reasoning.

This version works with whatever LLM is calling the MCP server,
rather than making its own API calls. Perfect for Cursor, Claude Desktop,
ChatGPT/Codex, VS Code, or any MCP-compatible environment.
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

import anyio

import hegelion
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from hegelion.mcp.constants import MCP_SCHEMA_VERSION, ToolName
from hegelion.mcp.handlers import (
    handle_antithesis_prompt,
    handle_autocoding_advance,
    handle_autocoding_init,
    handle_autocoding_load,
    handle_autocoding_save,
    handle_autocoding_single_shot,
    handle_autocoding_workflow,
    handle_coach_prompt,
    handle_dialectical_single_shot,
    handle_dialectical_workflow,
    handle_hegelion_entrypoint,
    handle_player_prompt,
    handle_synthesis_prompt,
    handle_thesis_prompt,
)
from hegelion.mcp.tooling import build_tools

app = Server("hegelion-server")

# Compatibility: older anyio versions expose create_memory_object_stream as a plain function
# which cannot be subscripted (newer typing style uses subscripting). Patch a lightweight
# wrapper so the MCP server session setup does not crash when subscripting is attempted.
if not hasattr(anyio.create_memory_object_stream, "__getitem__"):
    _create_stream = anyio.create_memory_object_stream

    class _CreateStreamWrapper:
        def __call__(self, *args, **kwargs):
            return _create_stream(*args, **kwargs)

        def __getitem__(self, _):
            return self

    anyio.create_memory_object_stream = _CreateStreamWrapper()  # type: ignore[assignment]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return dialectical reasoning tools that work with any LLM."""
    return build_tools()


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    """Execute dialectical reasoning tools."""

    if name == ToolName.DIALECTICAL_WORKFLOW.value:
        return await handle_dialectical_workflow(app, arguments)
    if name == ToolName.DIALECTICAL_SINGLE_SHOT.value:
        return await handle_dialectical_single_shot(app, arguments)
    if name == ToolName.THESIS_PROMPT.value:
        return await handle_thesis_prompt(app, arguments)
    if name == ToolName.ANTITHESIS_PROMPT.value:
        return await handle_antithesis_prompt(app, arguments)
    if name == ToolName.SYNTHESIS_PROMPT.value:
        return await handle_synthesis_prompt(app, arguments)
    if name == ToolName.HEGELION.value:
        return await handle_hegelion_entrypoint(app, arguments)
    if name == ToolName.AUTOCODING_INIT.value:
        return await handle_autocoding_init(app, arguments)
    if name == ToolName.AUTOCODING_WORKFLOW.value:
        return await handle_autocoding_workflow(app, arguments)
    if name == ToolName.PLAYER_PROMPT.value:
        return await handle_player_prompt(app, arguments)
    if name == ToolName.COACH_PROMPT.value:
        return await handle_coach_prompt(app, arguments)
    if name == ToolName.AUTOCODING_ADVANCE.value:
        return await handle_autocoding_advance(app, arguments)
    if name == ToolName.AUTOCODING_SINGLE_SHOT.value:
        return await handle_autocoding_single_shot(app, arguments)
    if name == ToolName.AUTOCODING_SAVE.value:
        return await handle_autocoding_save(app, arguments)
    if name == ToolName.AUTOCODING_LOAD.value:
        return await handle_autocoding_load(app, arguments)

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        structuredContent={
            "schema_version": MCP_SCHEMA_VERSION,
            "error": f"Unknown tool: {name}",
        },
        isError=True,
    )


async def run_server() -> None:
    """Run the prompt-driven MCP server using the standard stdio transport."""

    init_options = app.create_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            init_options,
            # Stateless keeps older MCP runtimes happy if they call tools/list immediately
            # after initialization or skip explicit initialization notifications.
            stateless=True,
        )


def main() -> None:
    """Main entry point for the prompt-driven MCP server."""
    parser = argparse.ArgumentParser(
        description="Hegelion Prompt-Driven MCP Server - Works with any LLM",
        add_help=True,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"hegelion {hegelion.__version__}",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run an in-process tool check (list tools + single-shot prompt) and exit",
    )
    args = parser.parse_args()

    if args.self_test:
        anyio.run(_self_test)
    else:
        anyio.run(run_server)


async def _self_test() -> None:
    """Self-test: list tools and call a sample tool so users see output."""

    print("🔎 Hegelion MCP self-test (in-process)")
    tools = await list_tools()
    tool_names = [t.name for t in tools]
    print("Tools:", ", ".join(tool_names))

    contents, structured = await call_tool(
        name=ToolName.DIALECTICAL_SINGLE_SHOT.value,
        arguments={
            "query": "Self-test: Can AI be genuinely creative?",
            "use_council": True,
            "response_style": "json",
        },
    )

    print("\nresponse_style: json")
    print("Structured keys:", list(structured.keys()))
    prompt = structured.get("prompt", "")
    print("Prompt preview:\n", prompt[:400], "...", sep="")
    print("\n✅ Self-test complete")


if __name__ == "__main__":
    main()
