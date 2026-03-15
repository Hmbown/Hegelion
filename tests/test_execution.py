"""Tests for execution backend selection and Codex-backed retries."""

from __future__ import annotations

import pytest

from hegelion.mcp import execution


def test_resolve_requested_backend_defaults_to_auto(monkeypatch):
    monkeypatch.delenv(execution.ENV_EXECUTION_BACKEND, raising=False)
    monkeypatch.delenv(execution.ENV_AUTOCOACH_BACKEND, raising=False)

    assert execution.resolve_requested_backend() == "auto"


def test_resolve_requested_backend_coach_prefers_autocoach_env(monkeypatch):
    monkeypatch.setenv(execution.ENV_EXECUTION_BACKEND, "cli")
    monkeypatch.setenv(execution.ENV_AUTOCOACH_BACKEND, "codex_mcp")

    assert execution.resolve_requested_backend(role="coach") == "codex_mcp"
    assert execution.resolve_requested_backend(role="player") == "cli"


@pytest.mark.asyncio
async def test_execute_prompt_auto_prefers_codex(monkeypatch):
    calls: list[str] = []

    async def fake_execute_with_backend(backend_selected, prompt, **kwargs):
        del prompt, kwargs
        calls.append(backend_selected)
        return execution.ExecutionResult(
            backend_requested="auto",
            backend_selected=backend_selected,
            executed=True,
            output="ok",
        )

    monkeypatch.setattr(execution, "_execute_with_backend", fake_execute_with_backend)

    result = await execution.execute_prompt("hello", backend="auto")

    assert calls == ["codex_mcp"]
    assert result.backend_selected == "codex_mcp"
    assert result.output == "ok"


@pytest.mark.asyncio
async def test_execute_prompt_auto_falls_back_to_cli(monkeypatch):
    calls: list[str] = []

    async def fake_execute_with_backend(backend_selected, prompt, **kwargs):
        del prompt, kwargs
        calls.append(backend_selected)
        if backend_selected == "codex_mcp":
            raise execution.BackendUnavailableError("codex missing")
        return execution.ExecutionResult(
            backend_requested="auto",
            backend_selected="cli",
            executed=True,
            output="cli output",
        )

    monkeypatch.setattr(execution, "_execute_with_backend", fake_execute_with_backend)

    result = await execution.execute_prompt("hello", backend="auto")

    assert calls == ["codex_mcp", "cli"]
    assert result.backend_selected == "cli"
    assert result.output == "cli output"


@pytest.mark.asyncio
async def test_execute_prompt_auto_falls_back_to_prompt(monkeypatch):
    async def fake_execute_with_backend(backend_selected, prompt, **kwargs):
        del backend_selected, prompt, kwargs
        raise execution.BackendUnavailableError("missing")

    monkeypatch.setattr(execution, "_execute_with_backend", fake_execute_with_backend)

    result = await execution.execute_prompt("hello", backend="auto")

    assert result.executed is False
    assert result.backend_selected == "prompt"
    assert "No executable backend available" in result.execution_skipped_reason


@pytest.mark.asyncio
async def test_execute_prompt_explicit_backend_is_strict(monkeypatch):
    async def fake_execute_with_backend(backend_selected, prompt, **kwargs):
        del backend_selected, prompt, kwargs
        raise execution.BackendUnavailableError("missing")

    monkeypatch.setattr(execution, "_execute_with_backend", fake_execute_with_backend)

    with pytest.raises(execution.BackendUnavailableError, match="missing"):
        await execution.execute_prompt("hello", backend="codex_mcp")


@pytest.mark.asyncio
async def test_execute_prompt_auto_does_not_fallback_on_runtime_failure(monkeypatch):
    calls: list[str] = []

    async def fake_execute_with_backend(backend_selected, prompt, **kwargs):
        del prompt, kwargs
        calls.append(backend_selected)
        raise execution.BackendExecutionError("backend failed")

    monkeypatch.setattr(execution, "_execute_with_backend", fake_execute_with_backend)

    with pytest.raises(execution.BackendExecutionError, match="backend failed"):
        await execution.execute_prompt("hello", backend="auto")

    assert calls == ["codex_mcp"]


@pytest.mark.asyncio
async def test_execute_with_codex_mcp_reuses_same_session_for_retries(monkeypatch):
    monkeypatch.setattr(
        execution,
        "_load_codex_settings",
        lambda env: (["codex", "mcp-server"], "gpt-5.4", "read-only", "never"),
    )

    class FakeCodexSession:
        instances: list["FakeCodexSession"] = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.prompts: list[str] = []
            self.thread_id: str | None = None
            FakeCodexSession.instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def run_prompt(self, prompt: str):
            self.prompts.append(prompt)
            if len(self.prompts) == 1:
                self.thread_id = "thread-1"
                return "BAD", {"thread_id": self.thread_id, "tool_name": "codex"}
            return "COACH APPROVED", {"thread_id": self.thread_id, "tool_name": "codex-reply"}

    monkeypatch.setattr(execution, "CodexMcpSession", FakeCodexSession)

    def validator(output: str):
        if output == "COACH APPROVED":
            return True, None
        return False, "Missing approval marker"

    result = await execution.execute_prompt(
        "Verify the implementation.",
        backend="codex_mcp",
        max_retries=1,
        validator=validator,
    )

    session = FakeCodexSession.instances[0]
    assert len(FakeCodexSession.instances) == 1
    assert session.prompts[0] == "Verify the implementation."
    assert "Missing approval marker" in session.prompts[1]
    assert result.output == "COACH APPROVED"
    assert result.details["attempts"] == 2
    assert result.details["thread_id"] == "thread-1"
    assert result.details["codex_tool"] == "codex-reply"
