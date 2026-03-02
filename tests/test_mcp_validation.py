"""Tests for MCP validation helpers and @validated decorator."""

import pytest
from mcp.types import CallToolResult

from hegelion.core.autocoding_state import AutocodingState
from hegelion.mcp.validation import (
    Bool,
    Enum,
    Int,
    Num,
    OptStr,
    State,
    Str,
    get_enum_arg,
    get_optional_bool,
    get_optional_int,
    get_optional_number,
    parse_autocoding_state,
    require_str_arg,
    validated,
)


def test_require_str_arg_invalid():
    result = require_str_arg("tool", {}, "query")

    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert result.structuredContent["error"] == "Invalid argument: query"
    assert result.structuredContent["expected"] == "non-empty string"


def test_require_str_arg_valid():
    result = require_str_arg("tool", {"query": "hi"}, "query")

    assert result == "hi"


def test_get_enum_arg_invalid():
    result = get_enum_arg("tool", {"format": "bad"}, "format", {"one", "two"}, "one")

    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert result.structuredContent["expected"] == ["one", "two"]
    assert result.structuredContent["received"] == "bad"


def test_get_optional_bool_invalid():
    result = get_optional_bool("tool", {"use_search": "yes"}, "use_search", False)

    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert result.structuredContent["expected"] == "boolean"


def test_get_optional_int_rejects_bool():
    result = get_optional_int("tool", {"max_turns": True}, "max_turns", 3, min_value=1)

    assert isinstance(result, CallToolResult)
    assert result.isError is True


def test_get_optional_number_bounds():
    result = get_optional_number("tool", {"score": 2.0}, "score", 0.5, min_value=0.0, max_value=1.0)

    assert isinstance(result, CallToolResult)
    assert result.isError is True


def test_parse_autocoding_state_invalid_type():
    result = parse_autocoding_state("tool", "not-a-dict")

    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert "Invalid autocoding state" in result.structuredContent["error"]


def test_parse_autocoding_state_valid():
    state = AutocodingState.create(requirements="- [ ] Test\n")

    parsed = parse_autocoding_state("tool", state.to_dict())

    assert isinstance(parsed, AutocodingState)
    assert parsed.session_id == state.session_id


# ---------------------------------------------------------------------------
# @validated decorator tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidatedDecorator:
    async def test_str_required(self):
        @validated("test_tool", query=Str())
        async def handler(app, *, query, _arguments):
            return query

        assert await handler(None, {"query": "hello"}) == "hello"

    async def test_str_missing_returns_error(self):
        @validated("test_tool", query=Str())
        async def handler(app, *, query, _arguments):
            return query

        result = await handler(None, {})
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert result.structuredContent["tool"] == "test_tool"

    async def test_enum_default(self):
        @validated("test_tool", mode=Enum(allowed={"a", "b"}, default="a"))
        async def handler(app, *, mode, _arguments):
            return mode

        assert await handler(None, {}) == "a"
        assert await handler(None, {"mode": "b"}) == "b"

    async def test_enum_invalid(self):
        @validated("test_tool", mode=Enum(allowed={"a", "b"}, default="a"))
        async def handler(app, *, mode, _arguments):
            return mode

        result = await handler(None, {"mode": "c"})
        assert isinstance(result, CallToolResult)
        assert result.isError is True

    async def test_bool_default(self):
        @validated("test_tool", flag=Bool(default=True))
        async def handler(app, *, flag, _arguments):
            return flag

        assert await handler(None, {}) is True
        assert await handler(None, {"flag": False}) is False

    async def test_int_with_min(self):
        @validated("test_tool", count=Int(default=5, min_value=1))
        async def handler(app, *, count, _arguments):
            return count

        assert await handler(None, {}) == 5
        assert await handler(None, {"count": 3}) == 3

        result = await handler(None, {"count": 0})
        assert isinstance(result, CallToolResult)
        assert result.isError is True

    async def test_num_with_range(self):
        @validated("test_tool", temp=Num(default=0.5, min_value=0.0, max_value=1.0))
        async def handler(app, *, temp, _arguments):
            return temp

        assert await handler(None, {}) == 0.5
        result = await handler(None, {"temp": 2.0})
        assert isinstance(result, CallToolResult)
        assert result.isError is True

    async def test_opt_str(self):
        @validated("test_tool", name=OptStr(default=None))
        async def handler(app, *, name, _arguments):
            return name

        assert await handler(None, {}) is None
        assert await handler(None, {"name": "foo"}) == "foo"

    async def test_state_spec(self):
        state = AutocodingState.create(requirements="test", max_turns=3)

        @validated("test_tool", state=State())
        async def handler(app, *, state, _arguments):
            return state

        result = await handler(None, {"state": state.to_dict()})
        assert isinstance(result, AutocodingState)

    async def test_multiple_specs(self):
        @validated(
            "test_tool",
            query=Str(),
            mode=Enum(allowed={"fast", "slow"}, default="fast"),
            verbose=Bool(default=False),
        )
        async def handler(app, *, query, mode, verbose, _arguments):
            return {"query": query, "mode": mode, "verbose": verbose}

        result = await handler(None, {"query": "hello"})
        assert result == {"query": "hello", "mode": "fast", "verbose": False}

    async def test_arguments_passthrough(self):
        @validated("test_tool", query=Str())
        async def handler(app, *, query, _arguments):
            return _arguments

        result = await handler(None, {"query": "hello", "extra": 42})
        assert result == {"query": "hello", "extra": 42}

    async def test_first_error_wins(self):
        @validated("test_tool", a=Str(), b=Str())
        async def handler(app, *, a, b, _arguments):
            return (a, b)

        result = await handler(None, {})
        assert isinstance(result, CallToolResult)
        assert result.isError is True
