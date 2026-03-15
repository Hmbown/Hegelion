from __future__ import annotations

import logging
from contextlib import AsyncExitStack, contextmanager
from datetime import timedelta
from typing import Any, Iterator, Sequence

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class _CodexEventWarningFilter(logging.Filter):
    """Suppress noisy Codex-specific notifications from the stock Python MCP client."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not ("Failed to validate notification" in message and "codex/event" in message)


@contextmanager
def suppress_codex_event_warnings() -> Iterator[None]:
    """Temporarily filter MCP validation warnings for Codex-only notifications."""

    root_logger = logging.getLogger()
    record_filter = _CodexEventWarningFilter()
    handlers = list(root_logger.handlers)

    root_logger.addFilter(record_filter)
    for handler in handlers:
        handler.addFilter(record_filter)

    try:
        yield
    finally:
        root_logger.removeFilter(record_filter)
        for handler in handlers:
            handler.removeFilter(record_filter)


def _extract_text_content(content_blocks: Sequence[Any]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            parts.append(text)
    return "\n".join(parts).strip()


def _result_error_message(result: Any) -> str:
    structured = result.structuredContent if isinstance(result.structuredContent, dict) else {}
    if isinstance(structured.get("error"), str):
        return structured["error"]

    text = _extract_text_content(result.content)
    if text:
        return text

    return "Codex MCP tool call failed"


class CodexMcpSession:
    """Thin stdio client wrapper around Codex's MCP server."""

    def __init__(
        self,
        *,
        command: Sequence[str],
        cwd: str,
        timeout_seconds: int,
        model: str | None = None,
        sandbox: str | None = None,
        approval_policy: str | None = None,
    ) -> None:
        if not command:
            raise ValueError("Codex MCP command must not be empty")

        self.command = list(command)
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.sandbox = sandbox
        self.approval_policy = approval_policy
        self.thread_id: str | None = None

        self._stack: AsyncExitStack | None = None
        self._client: ClientSession | None = None

    async def __aenter__(self) -> "CodexMcpSession":
        self._stack = AsyncExitStack()
        params = StdioServerParameters(
            command=self.command[0],
            args=self.command[1:],
            cwd=self.cwd,
        )

        with suppress_codex_event_warnings():
            read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
            self._client = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._client.initialize()

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._client = None

    async def run_prompt(self, prompt: str) -> tuple[str, dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("Codex MCP session is not open")

        if self.thread_id:
            tool_name = "codex-reply"
            arguments: dict[str, Any] = {
                "threadId": self.thread_id,
                "prompt": prompt,
            }
        else:
            tool_name = "codex"
            arguments = {
                "prompt": prompt,
                "cwd": self.cwd,
            }
            if self.model:
                arguments["model"] = self.model
            if self.sandbox:
                arguments["sandbox"] = self.sandbox
            if self.approval_policy:
                arguments["approval-policy"] = self.approval_policy

        with suppress_codex_event_warnings():
            result = await self._client.call_tool(
                tool_name,
                arguments,
                read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
            )

        if result.isError:
            raise RuntimeError(_result_error_message(result))

        structured = result.structuredContent if isinstance(result.structuredContent, dict) else {}
        output = structured.get("content") if isinstance(structured.get("content"), str) else None
        if output is None:
            output = _extract_text_content(result.content)

        thread_id = structured.get("threadId")
        if isinstance(thread_id, str) and thread_id:
            self.thread_id = thread_id

        return output.strip(), {
            "thread_id": self.thread_id,
            "tool_name": tool_name,
        }
