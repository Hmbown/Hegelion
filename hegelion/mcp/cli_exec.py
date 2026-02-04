from __future__ import annotations

import json
import os
import shlex
from typing import Mapping, Sequence

import anyio

DEFAULT_TIMEOUT_SECONDS = 120
ENV_LLM_COMMAND = "HEGELION_LLM_COMMAND"
ENV_LLM_COMMAND_JSON = "HEGELION_LLM_COMMAND_JSON"
ENV_AUTO_EXECUTE = "HEGELION_MCP_AUTO_EXECUTE"


def auto_execute_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    raw = env.get(ENV_AUTO_EXECUTE, "")
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_llm_command(env: Mapping[str, str] | None = None) -> list[str] | None:
    """Load a CLI command to run an LLM from environment variables.

    Preferred: HEGELION_LLM_COMMAND_JSON='["cmd","arg1",...]'
    Fallback:  HEGELION_LLM_COMMAND='cmd arg1 arg2'
    """

    env = env or os.environ

    cmd_json = (env.get(ENV_LLM_COMMAND_JSON) or "").strip()
    if cmd_json:
        parsed = json.loads(cmd_json)
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError(f"{ENV_LLM_COMMAND_JSON} must be a JSON array of strings")
        command = [item for item in parsed if item.strip()]
        if not command:
            raise ValueError(f"{ENV_LLM_COMMAND_JSON} must not be empty")
        return command

    cmd = (env.get(ENV_LLM_COMMAND) or "").strip()
    if not cmd:
        return None
    command = [part for part in shlex.split(cmd) if part.strip()]
    if not command:
        raise ValueError(f"{ENV_LLM_COMMAND} must not be empty")
    return command


async def run_llm_command(
    command: Sequence[str],
    prompt: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[str, str, int]:
    """Run an LLM CLI command with `prompt` on stdin and return (stdout, stderr, returncode)."""

    input_bytes = prompt.encode("utf-8")
    try:
        with anyio.fail_after(timeout_seconds):
            result = await anyio.run_process(list(command), input=input_bytes, check=False)
    except TimeoutError as exc:  # pragma: no cover (timing-dependent)
        raise TimeoutError(f"LLM CLI timed out after {timeout_seconds}s") from exc
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"LLM CLI not found: {command[0]}") from exc

    stdout = (result.stdout or b"").decode("utf-8", errors="replace")
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    return stdout, stderr, int(result.returncode)


def validate_llm_output(output: str, response_style: str) -> tuple[bool, str | None]:
    """Light validation to catch obvious format failures.

    Intended for best-effort retries, not strict parsing.
    """

    text = output.strip()
    if not text:
        return False, "Empty output"

    if response_style == "json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            return False, f"Invalid JSON: {exc}"
        if not isinstance(parsed, dict):
            return False, "JSON output must be an object"
        required = {"query", "thesis", "antithesis", "synthesis"}
        missing = sorted(required - set(parsed.keys()))
        if missing:
            return False, f"JSON output missing keys: {missing}"
        return True, None

    if response_style == "sections":
        required_markers = ("## THESIS", "## ANTITHESIS", "## SYNTHESIS")
        missing = [m for m in required_markers if m not in text]
        if missing:
            return False, f"Missing section headings: {missing}"
        return True, None

    if response_style == "bullet_points":
        required_markers = ("**Thesis**", "**Antithesis**", "**Synthesis**")
        missing = [m for m in required_markers if m not in text]
        if missing:
            return False, f"Missing bullet labels: {missing}"
        return True, None

    return True, None
