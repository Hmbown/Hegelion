"""Tests for model-agnostic MCP server."""

import json
import pytest
from mcp.types import CallToolResult
from hegelion.mcp.server import call_tool, list_tools


@pytest.mark.asyncio
class TestPromptMCPServer:
    async def test_list_tools(self):
        """Test that exactly 4 tools are listed."""
        tools = await list_tools()
        tool_names = sorted(t.name for t in tools)

        assert tool_names == ["autocode", "autocode_session", "autocode_turn", "dialectic"]

    async def test_dialectic_workflow(self):
        """Test dialectic tool in workflow mode."""
        args = {"query": "test query", "mode": "workflow"}
        content, workflow = await call_tool("dialectic", args)

        assert len(content) >= 1
        assert content[-1].type == "text"
        assert workflow["query"] == "test query"
        assert len(workflow["steps"]) >= 3
        assert workflow["instructions"]["response_style"] == "sections"

    async def test_dialectic_single_shot(self, monkeypatch):
        """Test dialectic tool in single_shot mode."""
        monkeypatch.delenv("HEGELION_MCP_AUTO_EXECUTE", raising=False)
        args = {"query": "test query", "mode": "single_shot", "use_council": True}
        contents, structured = await call_tool("dialectic", args)

        assert len(contents) == 1
        prompt = contents[0].text
        assert "test query" in prompt
        assert "THE LOGICIAN" in prompt
        assert structured["response_style"] == "sections"

    async def test_dialectic_execute_via_cli(self, monkeypatch):
        """Test dialectic execution via configured CLI."""
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
            "dialectic",
            {
                "query": "test query",
                "mode": "single_shot",
                "execute": True,
                "response_style": "sections",
            },
        )

        assert len(contents) == 1
        text = contents[0].text
        assert "## THESIS" in text
        assert structured["mode"] == "executed"
        assert structured["returncode"] == 0

    async def test_dialectic_thesis_mode(self):
        """Test dialectic thesis mode."""
        contents, structured = await call_tool(
            "dialectic", {"query": "test query", "mode": "thesis"}
        )
        assert structured["phase"] == "thesis"
        assert "THESIS PROMPT" in contents[0].text

    async def test_dialectic_antithesis_mode(self):
        """Test dialectic antithesis mode."""
        contents, structured = await call_tool(
            "dialectic", {"query": "test query", "mode": "antithesis", "thesis": "some thesis"}
        )
        assert structured["phase"] == "antithesis"
        assert "some thesis" in contents[0].text

    async def test_dialectic_antithesis_council(self):
        """Test antithesis council mode."""
        contents, structured = await call_tool(
            "dialectic",
            {"query": "test query", "mode": "antithesis", "thesis": "T", "use_council": True},
        )
        assert structured["phase"] == "antithesis_council"
        assert len(structured["prompts"]) == 3

    async def test_dialectic_synthesis_mode(self):
        """Test dialectic synthesis mode."""
        contents, structured = await call_tool(
            "dialectic",
            {"query": "test query", "mode": "synthesis", "thesis": "T", "antithesis": "A"},
        )
        assert structured["phase"] == "synthesis"

    async def test_dialectic_json_response_style(self):
        """Ensure response_style alters the returned prompt."""
        contents, structured = await call_tool(
            "dialectic",
            {
                "query": "test query",
                "mode": "workflow",
                "format": "single_prompt",
                "response_style": "json",
            },
        )
        assert "JSON" in contents[0].text
        assert structured["response_style"] == "json"

    async def test_autocode_workflow(self):
        """Test autocode in workflow mode."""
        requirements = "- [ ] Add auth\n- [ ] Add tests\n"
        contents, workflow = await call_tool(
            "autocode", {"requirements": requirements, "mode": "workflow", "max_turns": 3}
        )

        assert len(contents) == 2
        assert workflow["schema_version"] == 2
        assert workflow["workflow_type"] == "dialectical_autocoding"
        assert workflow["max_turns"] == 3

    async def test_autocode_init(self):
        """Test autocode init mode."""
        requirements = "- [ ] Add auth\n- [ ] Add tests\n"
        _, init_state = await call_tool(
            "autocode",
            {
                "requirements": requirements,
                "mode": "init",
                "max_turns": 2,
                "session_name": "auth-loop",
            },
        )

        assert init_state["schema_version"] == 2
        assert init_state["session_name"] == "auth-loop"
        assert init_state["phase"] == "player"

    async def test_autocode_turn_loop(self):
        """Verify init -> player -> coach -> advance transitions."""
        requirements = "- [ ] Add auth\n- [ ] Add tests\n"
        _, init_state = await call_tool(
            "autocode", {"requirements": requirements, "mode": "init", "max_turns": 2}
        )

        # Player turn
        _, player_struct = await call_tool("autocode_turn", {"role": "player", "state": init_state})

        assert player_struct["schema_version"] == 2
        assert player_struct["phase"] == "player"
        assert player_struct["current_phase"] == "player"
        assert player_struct["next_phase"] == "coach"
        assert player_struct["state"]["phase"] == "coach"

        # Coach turn
        _, coach_struct = await call_tool(
            "autocode_turn", {"role": "coach", "state": player_struct["state"]}
        )

        assert coach_struct["schema_version"] == 2
        assert coach_struct["phase"] == "coach"
        assert coach_struct["current_phase"] == "coach"

        # Advance
        _, advanced_state = await call_tool(
            "autocode_turn",
            {
                "role": "advance",
                "state": coach_struct["state"],
                "coach_feedback": "Not approved; add missing tests.",
                "approved": False,
            },
        )

        assert advanced_state["schema_version"] == 2
        assert advanced_state["phase"] == "player"
        assert advanced_state["current_turn"] == 1

    async def test_autocode_turn_invalid_transitions(self):
        """Invalid transitions should fail with expected/received phase and a hint."""
        requirements = "- [ ] Test\n"
        _, init_state = await call_tool("autocode", {"requirements": requirements, "mode": "init"})

        # coach expects coach phase, but we have player
        result = await call_tool("autocode_turn", {"role": "coach", "state": init_state})
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["expected"] == "coach"
        assert result.structuredContent["received"] == "player"
        assert "hint" in result.structuredContent

        # player expects player, but state from player_turn is coach
        _, player_struct = await call_tool("autocode_turn", {"role": "player", "state": init_state})
        result = await call_tool(
            "autocode_turn", {"role": "player", "state": player_struct["state"]}
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["expected"] == "player"
        assert result.structuredContent["received"] == "coach"

        # advance expects coach
        result = await call_tool(
            "autocode_turn",
            {"role": "advance", "state": init_state, "coach_feedback": "nope", "approved": False},
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["expected"] == "coach"
        assert result.structuredContent["received"] == "player"
