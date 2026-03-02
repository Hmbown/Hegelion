from __future__ import annotations

from hegelion.mcp.handlers.autocoding import (
    handle_autocode,
    handle_autocode_session,
    handle_autocode_turn,
)
from hegelion.mcp.handlers.dialectic import handle_dialectic

__all__ = [
    "handle_autocode",
    "handle_autocode_session",
    "handle_autocode_turn",
    "handle_dialectic",
]
