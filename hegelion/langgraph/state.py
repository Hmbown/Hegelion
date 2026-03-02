"""State and policy helpers for continuous dialectical coding graphs."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional, TypedDict

from hegelion.core.autocoding_state import AutocodingState

DialecticPhase = Literal[
    "observe",
    "thesis",
    "critique",
    "antithesis",
    "synthesis",
    "execute",
    "verify",
    "done",
    "halt",
]
DialecticStatus = Literal["active", "approved", "timeout", "failed"]
RiskLevel = Literal["low", "medium", "high"]

_RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_DESTRUCTIVE_PATTERNS = (
    re.compile(r"(^|\s)rm\s+-rf(\s|$)"),
    re.compile(r"(^|\s)git\s+reset\s+--hard(\s|$)"),
    re.compile(r"(^|\s)git\s+checkout\s+--(\s|$)"),
    re.compile(r"(^|\s)mkfs(\s|$)"),
    re.compile(r"(^|\s)dd\s+if=(/dev/zero|/dev/random)"),
)


@dataclass
class SynthesizedAction:
    """Action chosen after thesis + antithesis synthesis."""

    kind: str = "noop"
    target_files: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    risk_level: RiskLevel = "low"
    rationale: str = ""


@dataclass
class VerificationResult:
    """Execution verification payload."""

    tests_run: list[str] = field(default_factory=list)
    results: dict[str, str] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    passed: bool = False


@dataclass
class ApprovalState:
    """Tracks whether high-risk actions need/received human approval."""

    required: bool = False
    approved: Optional[bool] = None
    reason: Optional[str] = None


@dataclass
class TurnRecord:
    """Single turn trace for auditing/debugging."""

    turn: int
    builder_output: dict[str, Any]
    critic_output: dict[str, Any]
    synthesis_output: dict[str, Any]
    actions: dict[str, Any]
    verification: dict[str, Any]
    score: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        """Serialize record for state storage."""
        return asdict(self)


@dataclass
class DialecticPolicy:
    """Policy knobs for the continuous dialectical loop."""

    max_turns: int = 12
    approval_threshold: float = 0.9
    risk_interrupt_level: RiskLevel = "high"
    no_mutation_until_synthesis: bool = True


class DialecticTaskState(TypedDict):
    """State shape used by the LangGraph dialectic loop."""

    task_id: str
    objective: str
    requirements: str
    phase: DialecticPhase
    turn: int
    max_turns: int
    proposed_patch: Optional[str]
    critique: Optional[str]
    synthesized_action: dict[str, Any]
    verification: dict[str, Any]
    approval: dict[str, Any]
    score: Optional[float]
    history: list[dict[str, Any]]
    status: DialecticStatus
    observation: dict[str, Any]
    builder_output: dict[str, Any]
    critic_output: dict[str, Any]
    antithesis_output: dict[str, Any]
    synthesis_output: dict[str, Any]
    execution_result: dict[str, Any]
    autocoding_state: dict[str, Any]
    errors: list[str]


def normalize_risk_level(value: Optional[str], default: RiskLevel = "low") -> RiskLevel:
    """Normalize risk strings to known levels."""
    if value in _RISK_ORDER:
        return value  # type: ignore[return-value]
    return default


def command_is_destructive(command: str) -> bool:
    """Best-effort check for potentially destructive shell commands."""
    for pattern in _DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return True
    return False


def assess_risk(commands: list[str], explicit_risk: Optional[str] = None) -> RiskLevel:
    """Compute action risk from explicit label plus command heuristics."""
    explicit = normalize_risk_level(explicit_risk, default="low")
    computed = explicit
    if any(command_is_destructive(command) for command in commands):
        computed = "high"
    elif commands and computed == "low":
        computed = "medium"
    return computed


def risk_meets_threshold(risk_level: RiskLevel, threshold: RiskLevel) -> bool:
    """Return True if risk is at or above the policy threshold."""
    return _RISK_ORDER[risk_level] >= _RISK_ORDER[threshold]


def default_action() -> dict[str, Any]:
    """Default synthesized action payload."""
    return asdict(SynthesizedAction())


def default_verification() -> dict[str, Any]:
    """Default verification payload."""
    return asdict(VerificationResult())


def default_approval() -> dict[str, Any]:
    """Default approval payload."""
    return asdict(ApprovalState())


def create_initial_state(
    objective: str,
    requirements: str,
    policy: DialecticPolicy,
    *,
    task_id: Optional[str] = None,
    session_name: Optional[str] = None,
) -> DialecticTaskState:
    """Create a fresh state object for the continuous graph loop."""
    resolved_task_id = task_id or str(uuid.uuid4())
    autocoding_state = AutocodingState.create(
        requirements=requirements,
        max_turns=policy.max_turns,
        session_name=session_name,
    ).to_dict()

    return {
        "task_id": resolved_task_id,
        "objective": objective,
        "requirements": requirements,
        "phase": "observe",
        "turn": 0,
        "max_turns": policy.max_turns,
        "proposed_patch": None,
        "critique": None,
        "synthesized_action": default_action(),
        "verification": default_verification(),
        "approval": default_approval(),
        "score": None,
        "history": [],
        "status": "active",
        "observation": {},
        "builder_output": {},
        "critic_output": {},
        "antithesis_output": {},
        "synthesis_output": {},
        "execution_result": {},
        "autocoding_state": autocoding_state,
        "errors": [],
    }
