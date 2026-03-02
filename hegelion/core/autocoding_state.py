"""State management for dialectical autocoding sessions.

This module provides stateless state management for the coach-player
autocoding loop based on the g3 paper's adversarial cooperation paradigm.
State is passed explicitly between tool calls to maintain fresh context each turn.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from hegelion.core.constants import AutocodingPhase


@dataclass
class AutocodingState:
    """State for a dialectical autocoding session.

    This state is passed explicitly between tool calls, enabling fresh
    context each turn while maintaining session continuity.

    Attributes:
        session_id: Unique identifier for this autocoding session.
        session_name: Optional human-readable session label.
        requirements: The requirements document (source of truth).
        current_turn: Current turn number (0-indexed).
        max_turns: Maximum turns before timeout.
        phase: Current phase - player | coach | approved | timeout.
        turn_history: List of turn records with feedback.
        last_coach_feedback: Most recent coach feedback for player context.
    """

    session_id: str
    requirements: str
    session_name: Optional[str] = None
    current_turn: int = 0
    max_turns: int = 10
    phase: str = AutocodingPhase.PLAYER.value
    turn_history: List[Dict[str, Any]] = field(default_factory=list)
    last_coach_feedback: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate state after initialization."""
        valid_phases = AutocodingPhase.values()

        if self.phase not in valid_phases:
            raise ValueError(f"Invalid phase: {self.phase}. Must be one of {valid_phases}")

    @classmethod
    def create(
        cls,
        requirements: str,
        max_turns: int = 10,
        session_name: Optional[str] = None,
        **_kwargs: Any,
    ) -> "AutocodingState":
        """Create a new autocoding session.

        Args:
            requirements: The requirements document (source of truth).
            max_turns: Maximum turns before timeout.
            session_name: Optional human-readable session label.

        Returns:
            A new AutocodingState ready for the first player turn.
        """
        return cls(
            session_id=str(uuid.uuid4()),
            session_name=session_name,
            requirements=requirements,
            max_turns=max_turns,
            phase=AutocodingPhase.PLAYER.value,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to a dictionary for MCP transport.

        Returns:
            Dictionary representation of the state.
        """
        return {
            "schema_version": 2,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "requirements": self.requirements,
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "phase": self.phase,
            "turn_history": self.turn_history,
            "last_coach_feedback": self.last_coach_feedback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutocodingState":
        """Deserialize state from a dictionary.

        Handles v1 → v2 migration:
        - Ignores removed fields (status, quality_scores, approval_threshold)
        - Maps legacy phase="init" to phase="player"
        - Falls back to phase inferred from legacy status when possible

        Args:
            data: Dictionary representation of the state.

        Returns:
            Reconstructed AutocodingState.
        """
        valid_phases = AutocodingPhase.values()
        phase = data.get("phase")

        # Legacy v1 compatibility: INIT was removed in v2.
        if phase == "init":
            phase = AutocodingPhase.PLAYER.value

        if phase not in valid_phases:
            legacy_status = data.get("status")
            if legacy_status == "approved":
                phase = AutocodingPhase.APPROVED.value
            elif legacy_status == "timeout":
                phase = AutocodingPhase.TIMEOUT.value
            else:
                phase = AutocodingPhase.PLAYER.value

        return cls(
            session_id=data["session_id"],
            session_name=data.get("session_name"),
            requirements=data["requirements"],
            current_turn=data.get("current_turn", 0),
            max_turns=data.get("max_turns", 10),
            phase=phase,
            turn_history=data.get("turn_history", []),
            last_coach_feedback=data.get("last_coach_feedback"),
        )

    def advance_to_coach(self) -> "AutocodingState":
        """Advance state from player phase to coach phase.

        Returns:
            New state with coach phase active.

        Raises:
            ValueError: If not in player phase.
        """
        if self.phase != AutocodingPhase.PLAYER.value:
            raise ValueError(f"Cannot advance to coach from phase: {self.phase}")

        return AutocodingState(
            session_id=self.session_id,
            session_name=self.session_name,
            requirements=self.requirements,
            current_turn=self.current_turn,
            max_turns=self.max_turns,
            phase=AutocodingPhase.COACH.value,
            turn_history=self.turn_history.copy(),
            last_coach_feedback=self.last_coach_feedback,
        )

    def advance_turn(
        self,
        coach_feedback: str,
        approved: bool,
        **_kwargs: Any,
    ) -> "AutocodingState":
        """Advance state after coach review.

        Args:
            coach_feedback: Feedback from the coach agent.
            approved: Whether the coach approved the implementation.

        Returns:
            New state with updated turn, feedback, and phase.
        """
        if self.phase != AutocodingPhase.COACH.value:
            raise ValueError(f"Cannot advance turn from phase: {self.phase}")

        new_turn = self.current_turn + 1
        new_history = self.turn_history.copy()

        turn_record = {
            "turn": self.current_turn,
            "feedback": coach_feedback,
            "approved": approved,
        }
        new_history.append(turn_record)

        if approved:
            new_phase = AutocodingPhase.APPROVED.value
        elif new_turn >= self.max_turns:
            new_phase = AutocodingPhase.TIMEOUT.value
        else:
            new_phase = AutocodingPhase.PLAYER.value

        return AutocodingState(
            session_id=self.session_id,
            session_name=self.session_name,
            requirements=self.requirements,
            current_turn=new_turn,
            max_turns=self.max_turns,
            phase=new_phase,
            turn_history=new_history,
            last_coach_feedback=coach_feedback,
        )

    def is_complete(self) -> bool:
        """Check if the session has completed (approved or timeout).

        Returns:
            True if session is no longer active.
        """
        return self.phase in {
            AutocodingPhase.APPROVED.value,
            AutocodingPhase.TIMEOUT.value,
        }

    def turns_remaining(self) -> int:
        """Get the number of turns remaining.

        Returns:
            Number of turns left before timeout.
        """
        return max(0, self.max_turns - self.current_turn)

    def summary(self) -> str:
        """Generate a human-readable summary of session state.

        Returns:
            Summary string for display.
        """
        if self.session_name:
            session_label = f"{self.session_name} ({self.session_id[:8]}...)"
        else:
            session_label = f"{self.session_id[:8]}..."

        return (
            f"Session: {session_label}\n"
            f"Turn: {self.current_turn + 1}/{self.max_turns}\n"
            f"Phase: {self.phase}"
        )


def save_session(state: AutocodingState, filepath: str) -> None:
    """Save an autocoding session to a JSON file.

    Args:
        state: The AutocodingState to save.
        filepath: Path to save the session JSON file.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def load_session(filepath: str) -> AutocodingState:
    """Load an autocoding session from a JSON file.

    Args:
        filepath: Path to the session JSON file to load.

    Returns:
        Reconstructed AutocodingState.

    Raises:
        FileNotFoundError: If the session file doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the JSON doesn't contain valid session data.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Session file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return AutocodingState.from_dict(data)
