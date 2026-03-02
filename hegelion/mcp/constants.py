from __future__ import annotations

from enum import Enum

MCP_SCHEMA_VERSION = 2


class ToolName(str, Enum):
    DIALECTIC = "dialectic"
    AUTOCODE = "autocode"
    AUTOCODE_TURN = "autocode_turn"
    AUTOCODE_SESSION = "autocode_session"


RESPONSE_STYLE_ENUM = (
    "sections",
    "synthesis_only",
    "json",
)
RESPONSE_STYLES = set(RESPONSE_STYLE_ENUM)

WORKFLOW_FORMAT_ENUM = ("workflow", "single_prompt")
WORKFLOW_FORMATS = set(WORKFLOW_FORMAT_ENUM)

DIALECTIC_MODES_ENUM = ("single_shot", "workflow", "thesis", "antithesis", "synthesis")
DIALECTIC_MODES = set(DIALECTIC_MODES_ENUM)

AUTOCODE_MODES_ENUM = ("init", "workflow", "single_shot")
AUTOCODE_MODES = set(AUTOCODE_MODES_ENUM)

AUTOCODE_TURN_ROLES_ENUM = ("player", "coach", "advance")
AUTOCODE_TURN_ROLES = set(AUTOCODE_TURN_ROLES_ENUM)

AUTOCODE_SESSION_ACTIONS_ENUM = ("save", "load")
AUTOCODE_SESSION_ACTIONS = set(AUTOCODE_SESSION_ACTIONS_ENUM)
