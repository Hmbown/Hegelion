from __future__ import annotations

from typing import Any

from hegelion.core.constants import DialecticPhase

DIALECTIC_RESULT_SCHEMA = {
    "type": "object",
    "required": ["query", "thesis", "antithesis", "synthesis"],
    "properties": {
        "query": {"type": "string"},
        "thesis": {"type": "string"},
        "antithesis": {"type": "string"},
        "synthesis": {"type": "string"},
        "contradictions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["description", "evidence"],
                "properties": {
                    "description": {"type": "string"},
                    "evidence": {"type": "string"},
                },
            },
        },
        "research_proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["proposal", "testable_prediction"],
                "properties": {
                    "proposal": {"type": "string"},
                    "testable_prediction": {"type": "string"},
                },
            },
        },
    },
}

DIALECTIC_PHASE_SCHEMAS = {
    DialecticPhase.THESIS.value: {
        "type": "object",
        "required": ["phase", "thesis"],
        "properties": {
            "phase": {"type": "string"},
            "thesis": {"type": "string"},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
    },
    DialecticPhase.ANTITHESIS.value: {
        "type": "object",
        "required": ["phase", "antithesis", "contradictions"],
        "properties": {
            "phase": {"type": "string"},
            "antithesis": {"type": "string"},
            "contradictions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["description", "evidence"],
                    "properties": {
                        "description": {"type": "string"},
                        "evidence": {"type": "string"},
                    },
                },
            },
        },
    },
    DialecticPhase.SYNTHESIS.value: {
        "type": "object",
        "required": ["phase", "synthesis"],
        "properties": {
            "phase": {"type": "string"},
            "synthesis": {"type": "string"},
            "research_proposals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["proposal", "testable_prediction"],
                    "properties": {
                        "proposal": {"type": "string"},
                        "testable_prediction": {"type": "string"},
                    },
                },
            },
        },
    },
}


def response_style_summary(style: str) -> str:
    """Short human-readable description of response style."""
    match style:
        case "json":
            return "LLM should return a JSON object with thesis/antithesis/synthesis fields."
        case "synthesis_only":
            return "LLM should only return the synthesis (no thesis/antithesis sections)."
        case _:
            return "LLM should return full Thesis → Antithesis → Synthesis sections."


def response_schema_for_style(response_style: str) -> dict[str, Any] | None:
    if response_style != "json":
        return None
    return DIALECTIC_RESULT_SCHEMA


def phase_schema_for_style(response_style: str, phase: str) -> dict[str, Any] | None:
    if response_style != "json":
        return None
    if phase.startswith("council_"):
        phase = DialecticPhase.ANTITHESIS.value
    return DIALECTIC_PHASE_SCHEMAS.get(phase)
