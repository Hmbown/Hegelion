"""Node implementations for the continuous dialectical coding graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from hegelion.core.autocoding_state import AutocodingState
from hegelion.core.prompt_autocoding import PromptDrivenAutocoding
from hegelion.langgraph.state import (
    DialecticPolicy,
    DialecticTaskState,
    TurnRecord,
    assess_risk,
    default_approval,
    risk_meets_threshold,
)

ObserverFn = Callable[[DialecticTaskState], dict[str, Any]]
BuilderFn = Callable[[DialecticTaskState, str], dict[str, Any] | str]
CriticFn = Callable[[DialecticTaskState, str, dict[str, Any]], dict[str, Any] | str]
AntithesisFn = Callable[[DialecticTaskState, dict[str, Any], dict[str, Any]], dict[str, Any] | str]
SynthesizerFn = Callable[[DialecticTaskState, dict[str, Any], dict[str, Any]], dict[str, Any] | str]
ExecutorFn = Callable[[DialecticTaskState, dict[str, Any]], dict[str, Any]]
VerifierFn = Callable[[DialecticTaskState, dict[str, Any]], dict[str, Any]]
ApprovalFn = Callable[[DialecticTaskState, dict[str, Any]], tuple[bool, str]]


@dataclass
class DialecticRuntime:
    """Runtime callbacks used by LangGraph nodes for external effects."""

    observer: Optional[ObserverFn] = None
    builder: Optional[BuilderFn] = None
    critic: Optional[CriticFn] = None
    antithesis: Optional[AntithesisFn] = None
    synthesizer: Optional[SynthesizerFn] = None
    executor: Optional[ExecutorFn] = None
    verifier: Optional[VerifierFn] = None
    approval: Optional[ApprovalFn] = None


def _as_dict(payload: dict[str, Any] | str | None, key: str) -> dict[str, Any]:
    if payload is None:
        return {key: ""}
    if isinstance(payload, dict):
        return payload
    return {key: str(payload)}


def _autocoding_state_from_task(state: DialecticTaskState, errors: list[str]) -> AutocodingState:
    try:
        return AutocodingState.from_dict(state["autocoding_state"])
    except Exception as exc:
        errors.append(f"Invalid autocoding_state: {exc}")
        return AutocodingState.create(
            requirements=state["requirements"],
            max_turns=state["max_turns"],
            session_name=state["task_id"],
        )


def make_observe_node(runtime: DialecticRuntime) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create the observe node."""

    def observe_node(state: DialecticTaskState) -> dict[str, Any]:
        observation: dict[str, Any] = {}
        errors = list(state.get("errors", []))
        if runtime.observer is not None:
            try:
                observation = runtime.observer(state) or {}
            except Exception as exc:
                errors.append(f"Observer failed: {exc}")
                observation = {"error": str(exc)}

        return {
            "phase": "observe",
            "observation": observation,
            "errors": errors,
        }

    return observe_node


def make_thesis_node(
    runtime: DialecticRuntime, policy: DialecticPolicy
) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create the thesis (builder) node."""

    def thesis_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        autocoding_state = _autocoding_state_from_task(state, errors)
        prompt_engine = PromptDrivenAutocoding()
        player_prompt = prompt_engine.generate_player_prompt(
            requirements=state["requirements"],
            coach_feedback=autocoding_state.last_coach_feedback,
            turn_number=autocoding_state.current_turn + 1,
            max_turns=policy.max_turns,
        )

        if runtime.builder is None:
            builder_output = {
                "summary": "No builder callback configured. Provide DialecticRuntime.builder.",
                "commands": [],
                "target_files": [],
            }
        else:
            try:
                builder_output = _as_dict(
                    runtime.builder(state, player_prompt.prompt),
                    key="summary",
                )
            except Exception as exc:
                errors.append(f"Builder failed: {exc}")
                builder_output = {
                    "summary": f"Builder failed: {exc}",
                    "commands": [],
                    "target_files": [],
                }

        return {
            "phase": "thesis",
            "builder_output": builder_output,
            "proposed_patch": builder_output.get("proposed_patch"),
            "errors": errors,
        }

    return thesis_node


def make_critique_node(
    runtime: DialecticRuntime, policy: DialecticPolicy
) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create the critique node."""

    def critique_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        autocoding_state = _autocoding_state_from_task(state, errors)

        if autocoding_state.phase == "player":
            autocoding_state = autocoding_state.advance_to_coach()

        prompt_engine = PromptDrivenAutocoding()
        coach_prompt = prompt_engine.generate_coach_prompt(
            requirements=state["requirements"],
            turn_number=autocoding_state.current_turn + 1,
            max_turns=policy.max_turns,
        )

        if runtime.critic is None:
            critic_output = {
                "summary": "No critic callback configured. Provide DialecticRuntime.critic.",
                "blocking_issues": ["Missing critic callback"],
            }
        else:
            try:
                critic_output = _as_dict(
                    runtime.critic(state, coach_prompt.prompt, state["builder_output"]),
                    key="summary",
                )
            except Exception as exc:
                errors.append(f"Critic failed: {exc}")
                critic_output = {
                    "summary": f"Critic failed: {exc}",
                    "blocking_issues": [str(exc)],
                }

        return {
            "phase": "critique",
            "critic_output": critic_output,
            "critique": critic_output.get("summary", ""),
            "autocoding_state": autocoding_state.to_dict(),
            "errors": errors,
        }

    return critique_node


def make_antithesis_node(
    runtime: DialecticRuntime,
) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create the antithesis node from critique output."""

    def antithesis_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        builder_output = state.get("builder_output", {})
        critic_output = state.get("critic_output", {})

        if runtime.antithesis is None:
            antithesis_output = {
                "summary": critic_output.get("summary", ""),
                "counterproposal": critic_output.get(
                    "counterproposal",
                    "Refine thesis to satisfy critique constraints before execution.",
                ),
                "blocking_issues": critic_output.get("blocking_issues", []),
            }
        else:
            try:
                antithesis_output = _as_dict(
                    runtime.antithesis(state, builder_output, critic_output),
                    key="summary",
                )
            except Exception as exc:
                errors.append(f"Antithesis failed: {exc}")
                antithesis_output = {
                    "summary": f"Antithesis generation failed: {exc}",
                    "counterproposal": "",
                    "blocking_issues": [str(exc)],
                }

        return {
            "phase": "antithesis",
            "antithesis_output": antithesis_output,
            "errors": errors,
        }

    return antithesis_node


def make_synthesis_node(
    runtime: DialecticRuntime, policy: DialecticPolicy
) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create the synthesis node."""

    def synthesis_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        builder_output = state.get("builder_output", {})
        antithesis_output = state.get("antithesis_output", {}) or state.get("critic_output", {})

        if runtime.synthesizer is None:
            commands = builder_output.get("commands", [])
            target_files = builder_output.get("target_files", [])
            synthesis_output = {
                "kind": "run_commands" if commands else "noop",
                "target_files": target_files,
                "commands": commands,
                "risk_level": builder_output.get("risk_level", "low"),
                "rationale": "Default synthesis from builder output and critic notes.",
            }
        else:
            try:
                synthesis_output = _as_dict(
                    runtime.synthesizer(state, builder_output, antithesis_output),
                    key="rationale",
                )
            except Exception as exc:
                errors.append(f"Synthesizer failed: {exc}")
                synthesis_output = {
                    "kind": "noop",
                    "target_files": [],
                    "commands": [],
                    "risk_level": "high",
                    "rationale": f"Synthesizer failed: {exc}",
                }

        commands = list(synthesis_output.get("commands", []))
        risk_level = assess_risk(commands, explicit_risk=synthesis_output.get("risk_level"))
        requires_approval = risk_meets_threshold(risk_level, policy.risk_interrupt_level)
        approval = dict(state.get("approval", default_approval()))
        approval.update({"required": requires_approval})
        if not requires_approval:
            approval.update({"approved": True, "reason": "Low-risk action."})
        elif approval.get("approved") is True:
            approval["reason"] = approval.get("reason") or "Pre-approved."
        else:
            approval.update(
                {"approved": None, "reason": "Awaiting human approval for high-risk action."}
            )

        synthesis_output["risk_level"] = risk_level

        return {
            "phase": "synthesis",
            "synthesis_output": synthesis_output,
            "synthesized_action": synthesis_output,
            "approval": approval,
            "errors": errors,
        }

    return synthesis_node


def route_policy_gate(state: DialecticTaskState) -> str:
    """Route from policy gate to execution or approval."""
    approval = state.get("approval", {})
    if approval.get("required") and approval.get("approved") is not True:
        return "human_approval"
    return "execute"


def _interrupt_for_approval(payload: dict[str, Any]) -> Optional[tuple[bool, str]]:
    """Ask for human approval via LangGraph interrupt if available."""
    try:
        from langgraph.types import interrupt  # type: ignore
    except Exception:
        return None

    try:
        response = interrupt(payload)
    except Exception:
        return None

    if isinstance(response, dict):
        approved = bool(response.get("approved"))
        reason = str(
            response.get(
                "reason", "Approved via interrupt." if approved else "Denied via interrupt."
            )
        )
        return approved, reason
    if isinstance(response, bool):
        return response, "Approved via interrupt." if response else "Denied via interrupt."
    return None


def make_human_approval_node(
    runtime: DialecticRuntime,
) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create human-approval node."""

    def human_approval_node(state: DialecticTaskState) -> dict[str, Any]:
        approval = dict(state.get("approval", default_approval()))
        if not approval.get("required"):
            approval.update({"approved": True, "reason": "Approval not required."})
            return {"phase": "execute", "approval": approval}

        action = state.get("synthesized_action", {})
        decision: Optional[tuple[bool, str]] = None
        if runtime.approval is not None:
            try:
                decision = runtime.approval(state, action)
            except Exception as exc:
                decision = (False, f"Approval callback failed: {exc}")
        else:
            decision = _interrupt_for_approval(
                {
                    "task_id": state.get("task_id"),
                    "objective": state.get("objective"),
                    "action": action,
                    "message": "Approve high-risk synthesized action?",
                }
            )

        if decision is None:
            approval.update(
                {
                    "approved": False,
                    "reason": "Approval required but no callback/interrupt decision was available.",
                }
            )
            return {"phase": "halt", "approval": approval, "status": "failed"}

        approved, reason = decision
        approval.update({"approved": approved, "reason": reason})
        if not approved:
            return {"phase": "halt", "approval": approval, "status": "failed"}
        return {"phase": "execute", "approval": approval}

    return human_approval_node


def route_after_approval(state: DialecticTaskState) -> str:
    """Route after approval node."""
    approval = state.get("approval", {})
    if approval.get("approved") is True:
        return "execute"
    return "halt"


def make_execute_node(runtime: DialecticRuntime) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create action execution node."""

    def execute_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        approval = state.get("approval", {})
        if approval.get("required") and approval.get("approved") is not True:
            errors.append("Execution blocked because approval is required.")
            return {
                "phase": "halt",
                "status": "failed",
                "errors": errors,
            }

        action = state.get("synthesized_action", {})
        if runtime.executor is None:
            execution_result = {
                "executed": False,
                "reason": "No executor callback configured.",
                "commands": action.get("commands", []),
                "target_files": action.get("target_files", []),
            }
        else:
            try:
                execution_result = runtime.executor(state, action) or {}
            except Exception as exc:
                errors.append(f"Executor failed: {exc}")
                execution_result = {"executed": False, "error": str(exc)}

        return {
            "phase": "execute",
            "execution_result": execution_result,
            "errors": errors,
        }

    return execute_node


def make_verify_node(runtime: DialecticRuntime) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create verification node."""

    def verify_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        execution_result = state.get("execution_result", {})
        if runtime.verifier is None:
            failures = [execution_result.get("error")] if execution_result.get("error") else []
            verification = {
                "tests_run": [],
                "results": {},
                "failures": [item for item in failures if item],
                "passed": not failures,
            }
        else:
            try:
                verification = runtime.verifier(state, execution_result) or {}
            except Exception as exc:
                errors.append(f"Verifier failed: {exc}")
                verification = {
                    "tests_run": [],
                    "results": {},
                    "failures": [str(exc)],
                    "passed": False,
                }

        passed = bool(verification.get("passed"))
        raw_score = verification.get("score")
        score = float(raw_score) if raw_score is not None else (1.0 if passed else 0.0)
        return {
            "phase": "verify",
            "verification": verification,
            "score": score,
            "errors": errors,
        }

    return verify_node


def _coach_feedback_from_state(state: DialecticTaskState) -> str:
    critique = state.get("critique") or "No critique generated."
    verification = state.get("verification", {})
    failures = verification.get("failures", [])
    if failures:
        failure_text = "; ".join(str(failure) for failure in failures)
        return f"{critique}\n\nVerification failures: {failure_text}"
    if verification.get("passed"):
        return f"{critique}\n\nCOACH APPROVED"
    return critique


def make_advance_node(
    policy: DialecticPolicy,
) -> Callable[[DialecticTaskState], dict[str, Any]]:
    """Create turn-advancement node."""

    def advance_node(state: DialecticTaskState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        autocoding_state = _autocoding_state_from_task(state, errors)
        if autocoding_state.phase != "coach":
            autocoding_state = autocoding_state.advance_to_coach()

        score = state.get("score")
        verification = state.get("verification", {})
        approved = (
            verification.get("passed") is True
            and score is not None
            and score >= policy.approval_threshold
            and not errors
        )
        feedback = _coach_feedback_from_state(state)
        autocoding_state = autocoding_state.advance_turn(
            coach_feedback=feedback,
            approved=approved,
        )

        history = list(state.get("history", []))
        history.append(
            TurnRecord(
                turn=state.get("turn", 0),
                builder_output=state.get("builder_output", {}),
                critic_output=state.get("critic_output", {}),
                synthesis_output=state.get("synthesis_output", {}),
                actions=state.get("execution_result", {}),
                verification=verification,
                score=score,
            ).to_dict()
        )

        status = "active"
        phase = "thesis"
        if autocoding_state.phase == "approved":
            status = "approved"
            phase = "done"
        elif autocoding_state.phase == "timeout":
            status = "timeout"
            phase = "halt"
        elif state.get("status") == "failed":
            status = "failed"
            phase = "halt"

        next_approval = (
            default_approval() if status == "active" else state.get("approval", default_approval())
        )

        return {
            "phase": phase,
            "status": status,
            "turn": autocoding_state.current_turn,
            "history": history,
            "autocoding_state": autocoding_state.to_dict(),
            "approval": next_approval,
            "errors": errors,
        }

    return advance_node


def route_advance(state: DialecticTaskState) -> str:
    """Route from advance node to loop/done/halt."""
    status = state.get("status")
    if status == "approved":
        return "done"
    if status in {"timeout", "failed"}:
        return "halt"
    return "thesis"


def done_node(_: DialecticTaskState) -> dict[str, Any]:
    """Terminal success node."""
    return {"phase": "done"}


def halt_node(state: DialecticTaskState) -> dict[str, Any]:
    """Terminal failure/timeout node."""
    status = state.get("status", "failed")
    if status == "active":
        status = "failed"
    return {"phase": "halt", "status": status}
