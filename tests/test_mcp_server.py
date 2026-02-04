"""Tests for model-agnostic MCP server."""

import json
import pytest
from mcp.types import CallToolResult
from hegelion.mcp.server import call_tool, list_tools


@pytest.mark.asyncio
class TestPromptMCPServer:
    async def test_list_tools(self):
        """Test that all prompt tools are listed."""
        tools = await list_tools()
        tool_names = [t.name for t in tools]

        assert "dialectical_workflow" in tool_names
        assert "dialectical_single_shot" in tool_names
        assert "thesis_prompt" in tool_names
        assert "antithesis_prompt" in tool_names
        assert "synthesis_prompt" in tool_names
        assert "hegelion" in tool_names
        assert "autocoding_workflow" in tool_names

    async def test_dialectical_workflow_tool(self):
        """Test dialectical workflow tool execution."""
        args = {"query": "test query"}
        content, workflow = await call_tool("dialectical_workflow", args)

        assert len(content) >= 1
        assert content[-1].type == "text"

        assert workflow["query"] == "test query"
        assert len(workflow["steps"]) >= 3
        assert workflow["instructions"]["response_style"] == "sections"

    async def test_dialectical_single_shot_tool(self, monkeypatch):
        """Test single shot prompt tool."""
        monkeypatch.delenv("HEGELION_MCP_AUTO_EXECUTE", raising=False)
        args = {"query": "test query", "use_council": True}
        result = await call_tool("dialectical_single_shot", args)

        contents, structured = result
        assert len(contents) == 1
        prompt = contents[0].text
        assert "test query" in prompt
        assert "THE LOGICIAN" in prompt
        assert structured["response_style"] == "sections"

    async def test_dialectical_single_shot_execute_via_cli(self, monkeypatch):
        """Test single shot tool execution via configured CLI."""
        code = (
            "import sys\n"
            "data = sys.stdin.read()\n"
            "ok = 'test query' in data\n"
            "out = (\n"
            "  '## THESIS\\nT\\n\\n'\n"
            "  '## ANTITHESIS\\nA\\n\\n'\n"
            "  '## SYNTHESIS\\nS\\n'\n"
            ") if ok else 'BAD'\n"
            "sys.stdout.write(out)\n"
        )
        monkeypatch.setenv("HEGELION_LLM_COMMAND_JSON", json.dumps(["python3", "-c", code]))
        monkeypatch.delenv("HEGELION_MCP_AUTO_EXECUTE", raising=False)

        contents, structured = await call_tool(
            "dialectical_single_shot",
            {"query": "test query", "execute": True, "response_style": "sections"},
        )

        assert len(contents) == 1
        text = contents[0].text
        assert "## THESIS" in text
        assert "## ANTITHESIS" in text
        assert "## SYNTHESIS" in text
        assert structured["mode"] == "executed"
        assert structured["llm_cli"] == "python3"
        assert structured["returncode"] == 0
        assert structured["output"] == text

    async def test_thesis_prompt_tool(self):
        """Test thesis prompt tool."""
        args = {"query": "test query"}
        contents, structured = await call_tool("thesis_prompt", args)

        assert len(contents) == 1
        content = contents[0].text
        assert "THESIS PROMPT" in content
        assert "test query" in content
        assert structured["phase"] == "thesis"

    async def test_antithesis_prompt_tool(self):
        """Test antithesis prompt tool."""
        args = {"query": "test query", "thesis": "some thesis"}
        contents, structured = await call_tool("antithesis_prompt", args)

        content = contents[0].text
        assert "ANTITHESIS PROMPT" in content
        assert "test query" in content
        assert "some thesis" in content
        assert structured["phase"] == "antithesis"

    async def test_antithesis_council_prompt_tool(self):
        """Test antithesis prompt tool with council."""
        args = {"query": "test query", "thesis": "some thesis", "use_council": True}
        contents, structured = await call_tool("antithesis_prompt", args)

        content = contents[0].text
        assert "COUNCIL ANTITHESIS PROMPTS" in content
        assert "The Logician" in content
        assert structured["phase"] == "antithesis_council"
        assert len(structured["prompts"]) == 3

    async def test_synthesis_prompt_tool(self):
        """Test synthesis prompt tool."""
        args = {"query": "test query", "thesis": "T", "antithesis": "A"}
        contents, structured = await call_tool("synthesis_prompt", args)

        content = contents[0].text
        assert "SYNTHESIS PROMPT" in content
        assert "T" in content
        assert "A" in content
        assert structured["phase"] == "synthesis"

    async def test_single_prompt_json_response_style(self):
        """Ensure response_style alters the returned prompt."""
        args = {
            "query": "test query",
            "format": "single_prompt",
            "response_style": "json",
        }

        contents, structured = await call_tool("dialectical_workflow", args)

        assert "JSON" in contents[0].text
        assert structured["response_style"] == "json"

    async def test_autocoding_workflow_tool(self):
        """Ensure autocoding_workflow returns structured steps."""
        requirements = "- [ ] Add auth\n- [ ] Add tests\n"
        contents, workflow = await call_tool(
            "autocoding_workflow", {"requirements": requirements, "max_turns": 3}
        )

        assert len(contents) == 2
        assert workflow["schema_version"] == 1
        assert workflow["workflow_type"] == "dialectical_autocoding"
        assert workflow["max_turns"] == 3
        assert len(workflow["steps"]) >= 3

    async def test_hegelion_autocoding_entrypoint_workflow(self):
        """Ensure hegelion entrypoint can return autocoding workflow."""
        requirements = "- [ ] Add auth\n- [ ] Add tests\n"
        contents, workflow = await call_tool(
            "hegelion",
            {"requirements": requirements, "mode": "workflow", "max_turns": 2},
        )

        assert len(contents) == 2
        assert workflow["schema_version"] == 1
        assert workflow["workflow_type"] == "dialectical_autocoding"
        assert workflow["entrypoint"] == "hegelion"
        assert workflow["mode"] == "workflow"
        assert workflow["max_turns"] == 2

    async def test_autocoding_loop_transitions_and_schema(self):
        """Verify init -> player_prompt -> coach_prompt -> advance transitions and schema keys."""
        requirements = "- [ ] Add auth\n- [ ] Add tests\n"
        _, init_state = await call_tool(
            "autocoding_init",
            {"requirements": requirements, "max_turns": 2, "session_name": "auth-loop"},
        )

        assert init_state["schema_version"] == 1
        assert init_state["session_name"] == "auth-loop"
        assert init_state["phase"] == "player"
        assert init_state["status"] == "active"

        _, player_struct = await call_tool("player_prompt", {"state": init_state})

        expected_player_keys = {
            "schema_version",
            "phase",
            "prompt",
            "instructions",
            "expected_format",
            "requirements_embedded",
            "current_phase",
            "next_phase",
            "state",
        }
        assert expected_player_keys.issubset(player_struct.keys())
        assert player_struct["schema_version"] == 1
        assert player_struct["phase"] == "player"
        assert player_struct["current_phase"] == "player"
        assert player_struct["next_phase"] == "coach"
        assert player_struct["state"]["phase"] == "coach"

        _, coach_struct = await call_tool("coach_prompt", {"state": player_struct["state"]})

        expected_coach_keys = {
            "schema_version",
            "phase",
            "prompt",
            "instructions",
            "expected_format",
            "requirements_embedded",
            "current_phase",
            "next_phase",
            "state",
        }
        assert expected_coach_keys.issubset(coach_struct.keys())
        assert coach_struct["schema_version"] == 1
        assert coach_struct["phase"] == "coach"
        assert coach_struct["current_phase"] == "coach"
        assert coach_struct["next_phase"] == "coach"
        assert coach_struct["state"]["phase"] == "coach"

        _, advanced_state = await call_tool(
            "autocoding_advance",
            {
                "state": coach_struct["state"],
                "coach_feedback": "Not approved; add missing tests.",
                "approved": False,
            },
        )

        assert advanced_state["schema_version"] == 1
        assert advanced_state["phase"] == "player"
        assert advanced_state["status"] == "active"
        assert advanced_state["current_turn"] == 1

    async def test_autocoding_invalid_transitions_have_clear_errors(self):
        """Invalid transitions should fail with expected/received phase and a hint."""
        requirements = "- [ ] Test\n"
        _, init_state = await call_tool("autocoding_init", {"requirements": requirements})

        # coach_prompt expects coach, but we have player.
        result = await call_tool("coach_prompt", {"state": init_state})
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["expected"] == "coach"
        assert result.structuredContent["received"] == "player"
        assert "hint" in result.structuredContent

        # player_prompt expects player, but the state returned from player_prompt is coach.
        _, player_struct = await call_tool("player_prompt", {"state": init_state})
        result = await call_tool("player_prompt", {"state": player_struct["state"]})
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["expected"] == "player"
        assert result.structuredContent["received"] == "coach"
        assert "hint" in result.structuredContent

        # autocoding_advance expects coach.
        result = await call_tool(
            "autocoding_advance",
            {"state": init_state, "coach_feedback": "nope", "approved": False},
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["expected"] == "coach"
        assert result.structuredContent["received"] == "player"
