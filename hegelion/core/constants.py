from __future__ import annotations

from enum import Enum


class DialecticPhase(str, Enum):
    THESIS = "thesis"
    ANTITHESIS = "antithesis"
    SYNTHESIS = "synthesis"

    @classmethod
    def values(cls) -> set[str]:
        return {phase.value for phase in cls}


class AutocodingPhase(str, Enum):
    PLAYER = "player"
    COACH = "coach"
    APPROVED = "approved"
    TIMEOUT = "timeout"

    @classmethod
    def values(cls) -> set[str]:
        return {phase.value for phase in cls}
