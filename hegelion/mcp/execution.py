from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from hegelion.mcp.cli_exec import DEFAULT_TIMEOUT_SECONDS, load_llm_command, run_llm_command
from hegelion.mcp.codex_mcp_backend import CodexMcpSession
from hegelion.mcp.constants import EXECUTION_BACKENDS

ENV_EXECUTION_BACKEND = "HEGELION_EXECUTION_BACKEND"
ENV_AUTOCOACH_BACKEND = "HEGELION_AUTOCOACH_BACKEND"
ENV_CODEX_MCP_COMMAND_JSON = "HEGELION_CODEX_MCP_COMMAND_JSON"
ENV_CODEX_MODEL = "HEGELION_CODEX_MODEL"
ENV_CODEX_SANDBOX = "HEGELION_CODEX_SANDBOX"
ENV_CODEX_APPROVAL_POLICY = "HEGELION_CODEX_APPROVAL_POLICY"

DEFAULT_EXECUTION_BACKEND = "auto"
DEFAULT_AUTOCOACH_BACKEND = "auto"
DEFAULT_CODEX_MCP_COMMAND = ["codex", "mcp-server"]
DEFAULT_CODEX_SANDBOX = "read-only"
DEFAULT_CODEX_APPROVAL_POLICY = "never"

CODEX_SANDBOXES = {"read-only", "workspace-write", "danger-full-access"}
CODEX_APPROVAL_POLICIES = {"untrusted", "on-failure", "on-request", "never"}

ValidatorFn = Callable[[str], tuple[bool, str | None]]
RetryPromptBuilderFn = Callable[[str, str], str]


class BackendUnavailableError(RuntimeError):
    """Raised when a backend cannot be used due to availability or configuration."""


class BackendExecutionError(RuntimeError):
    """Raised when a backend was selected successfully but execution failed."""


@dataclass
class ExecutionResult:
    backend_requested: str
    backend_selected: str
    executed: bool
    output: str | None = None
    execution_skipped_reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        metadata = {
            "backend_requested": self.backend_requested,
            "backend_selected": self.backend_selected,
            "executed": self.executed,
        }
        if self.execution_skipped_reason:
            metadata["execution_skipped_reason"] = self.execution_skipped_reason
        metadata.update({key: value for key, value in self.details.items() if value is not None})
        if self.output is not None:
            metadata["output"] = self.output
        return metadata


def build_validation_retry_prompt(prompt: str, validation_error: str) -> str:
    return (
        f"{prompt}\n\nIMPORTANT: Your last response did not match the required format "
        f"({validation_error}). Re-run and strictly follow the output format instructions. "
        "Output only the final answer."
    )


def resolve_requested_backend(
    backend: str | None = None,
    *,
    role: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    env = env or os.environ

    raw_backend = backend
    if raw_backend is None and role == "coach":
        raw_backend = _get_optional_env(env, ENV_AUTOCOACH_BACKEND) or _get_optional_env(
            env, ENV_EXECUTION_BACKEND
        )
    if raw_backend is None:
        raw_backend = _get_optional_env(env, ENV_EXECUTION_BACKEND)

    requested = raw_backend or (
        DEFAULT_AUTOCOACH_BACKEND if role == "coach" else DEFAULT_EXECUTION_BACKEND
    )
    if requested not in EXECUTION_BACKENDS:
        raise ValueError(f"Unsupported execution backend: {requested}")
    return requested


def _get_optional_env(env: Mapping[str, str], key: str) -> str | None:
    value = (env.get(key) or "").strip()
    return value or None


def _load_codex_mcp_command(env: Mapping[str, str]) -> list[str]:
    raw = _get_optional_env(env, ENV_CODEX_MCP_COMMAND_JSON)
    if raw is None:
        return DEFAULT_CODEX_MCP_COMMAND.copy()

    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError(f"{ENV_CODEX_MCP_COMMAND_JSON} must be a JSON array of strings")

    command = [item for item in parsed if item.strip()]
    if not command:
        raise ValueError(f"{ENV_CODEX_MCP_COMMAND_JSON} must not be empty")
    return command


def _load_codex_settings(
    env: Mapping[str, str],
) -> tuple[list[str], str | None, str, str]:
    command = _load_codex_mcp_command(env)
    model = _get_optional_env(env, ENV_CODEX_MODEL)
    sandbox = _get_optional_env(env, ENV_CODEX_SANDBOX) or DEFAULT_CODEX_SANDBOX
    approval_policy = (
        _get_optional_env(env, ENV_CODEX_APPROVAL_POLICY) or DEFAULT_CODEX_APPROVAL_POLICY
    )

    if sandbox not in CODEX_SANDBOXES:
        raise ValueError(f"{ENV_CODEX_SANDBOX} must be one of {sorted(CODEX_SANDBOXES)}")
    if approval_policy not in CODEX_APPROVAL_POLICIES:
        raise ValueError(
            f"{ENV_CODEX_APPROVAL_POLICY} must be one of {sorted(CODEX_APPROVAL_POLICIES)}"
        )

    return command, model, sandbox, approval_policy


def _load_cli_command_or_raise(env: Mapping[str, str]) -> list[str]:
    try:
        command = load_llm_command(env)
    except (json.JSONDecodeError, ValueError) as exc:
        raise BackendUnavailableError(f"Invalid CLI configuration: {exc}") from exc

    if not command:
        raise BackendUnavailableError(
            "Missing CLI configuration: set HEGELION_LLM_COMMAND_JSON or HEGELION_LLM_COMMAND"
        )
    return command


async def execute_prompt(
    prompt: str,
    *,
    backend: str | None = None,
    role: str | None = None,
    cwd: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = 0,
    validator: ValidatorFn | None = None,
    retry_prompt_builder: RetryPromptBuilderFn | None = None,
    env: Mapping[str, str] | None = None,
) -> ExecutionResult:
    env = env or os.environ
    requested = resolve_requested_backend(backend, role=role, env=env)
    effective_cwd = cwd or os.getcwd()

    if requested == "prompt":
        return ExecutionResult(
            backend_requested=requested,
            backend_selected="prompt",
            executed=False,
            execution_skipped_reason="Prompt backend selected",
        )

    if requested == "auto":
        unavailable_reasons: list[str] = []
        for candidate in ("codex_mcp", "cli"):
            try:
                return await _execute_with_backend(
                    candidate,
                    prompt,
                    backend_requested=requested,
                    cwd=effective_cwd,
                    timeout_seconds=timeout_seconds,
                    max_retries=max_retries,
                    validator=validator,
                    retry_prompt_builder=retry_prompt_builder,
                    env=env,
                )
            except BackendUnavailableError as exc:
                unavailable_reasons.append(f"{candidate}: {exc}")

        return ExecutionResult(
            backend_requested=requested,
            backend_selected="prompt",
            executed=False,
            execution_skipped_reason=(
                "No executable backend available; returning prompt-only output. "
                + "; ".join(unavailable_reasons)
            ),
        )

    return await _execute_with_backend(
        requested,
        prompt,
        backend_requested=requested,
        cwd=effective_cwd,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        validator=validator,
        retry_prompt_builder=retry_prompt_builder,
        env=env,
    )


async def _execute_with_backend(
    backend_selected: str,
    prompt: str,
    *,
    backend_requested: str,
    cwd: str,
    timeout_seconds: int,
    max_retries: int,
    validator: ValidatorFn | None,
    retry_prompt_builder: RetryPromptBuilderFn | None,
    env: Mapping[str, str],
) -> ExecutionResult:
    if backend_selected == "cli":
        return await _execute_with_cli(
            prompt,
            backend_requested=backend_requested,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            validator=validator,
            retry_prompt_builder=retry_prompt_builder,
            env=env,
        )
    if backend_selected == "codex_mcp":
        return await _execute_with_codex_mcp(
            prompt,
            backend_requested=backend_requested,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            validator=validator,
            retry_prompt_builder=retry_prompt_builder,
            env=env,
        )
    raise ValueError(f"Unsupported execution backend: {backend_selected}")


async def _execute_with_cli(
    prompt: str,
    *,
    backend_requested: str,
    cwd: str,
    timeout_seconds: int,
    max_retries: int,
    validator: ValidatorFn | None,
    retry_prompt_builder: RetryPromptBuilderFn | None,
    env: Mapping[str, str],
) -> ExecutionResult:
    del cwd  # CLI execution does not currently override working directory.
    command = _load_cli_command_or_raise(env)

    attempt_prompt = prompt
    attempts = 0
    output = ""
    last_stderr = ""
    last_returncode = 0
    last_validation_error: str | None = None

    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        try:
            stdout, stderr, returncode = await run_llm_command(
                command, attempt_prompt, timeout_seconds=timeout_seconds
            )
        except FileNotFoundError as exc:
            raise BackendUnavailableError(str(exc)) from exc
        except TimeoutError as exc:
            raise BackendExecutionError(str(exc)) from exc

        output = stdout.strip()
        last_stderr = stderr.strip()
        last_returncode = returncode

        if returncode != 0:
            raise BackendExecutionError(
                f"LLM CLI exited with code {returncode}.\n\nstderr:\n{last_stderr}"
            )

        if validator is None:
            last_validation_error = None
            break

        valid, validation_error = validator(output)
        if valid:
            last_validation_error = None
            break

        last_validation_error = validation_error or "Validation failed"
        if attempt == max_retries:
            break
        attempt_prompt = (retry_prompt_builder or build_validation_retry_prompt)(
            prompt, last_validation_error
        )

    return ExecutionResult(
        backend_requested=backend_requested,
        backend_selected="cli",
        executed=True,
        output=output,
        details={
            "llm_cli": command[0],
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "attempts": attempts,
            "returncode": last_returncode,
            "stderr": last_stderr or None,
            "validation_error": last_validation_error,
        },
    )


async def _execute_with_codex_mcp(
    prompt: str,
    *,
    backend_requested: str,
    cwd: str,
    timeout_seconds: int,
    max_retries: int,
    validator: ValidatorFn | None,
    retry_prompt_builder: RetryPromptBuilderFn | None,
    env: Mapping[str, str],
) -> ExecutionResult:
    try:
        command, model, sandbox, approval_policy = _load_codex_settings(env)
    except (json.JSONDecodeError, ValueError) as exc:
        raise BackendUnavailableError(f"Invalid Codex MCP configuration: {exc}") from exc

    attempt_prompt = prompt
    attempts = 0
    output = ""
    last_details: dict[str, Any] = {}
    last_validation_error: str | None = None

    try:
        async with CodexMcpSession(
            command=command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            model=model,
            sandbox=sandbox,
            approval_policy=approval_policy,
        ) as session:
            for attempt in range(max_retries + 1):
                attempts = attempt + 1
                try:
                    output, last_details = await session.run_prompt(attempt_prompt)
                except RuntimeError as exc:
                    raise BackendExecutionError(str(exc)) from exc

                if validator is None:
                    last_validation_error = None
                    break

                valid, validation_error = validator(output)
                if valid:
                    last_validation_error = None
                    break

                last_validation_error = validation_error or "Validation failed"
                if attempt == max_retries:
                    break
                attempt_prompt = (retry_prompt_builder or build_validation_retry_prompt)(
                    prompt, last_validation_error
                )
    except FileNotFoundError as exc:
        raise BackendUnavailableError(str(exc)) from exc
    except OSError as exc:
        raise BackendUnavailableError(f"Unable to start Codex MCP backend: {exc}") from exc

    return ExecutionResult(
        backend_requested=backend_requested,
        backend_selected="codex_mcp",
        executed=True,
        output=output,
        details={
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "attempts": attempts,
            "thread_id": last_details.get("thread_id"),
            "codex_tool": last_details.get("tool_name"),
            "codex_mcp_command": command[0],
            "codex_model": model,
            "codex_sandbox": sandbox,
            "codex_approval_policy": approval_policy,
            "validation_error": last_validation_error,
        },
    )
