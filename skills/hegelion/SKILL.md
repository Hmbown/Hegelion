---
name: hegelion
description: Dialectical reasoning and autocoding via Hegelion MCP tools.
---

# Hegelion Skill

## Routing

| Task type | MCP call |
|-----------|----------|
| Analysis/decision | `mcp__hegelion__dialectic(query, mode="single_shot", response_style="synthesis_only")` |
| Implementation | `mcp__hegelion__autocode(requirements, mode="init")` |

Tip: If execution is configured, set `execute=true` and `backend="auto"` on `dialectic` mode=single_shot to return the final answer in one call.

## Autocoding Loop

```
mcp__hegelion__autocode(requirements, mode="init")
    -> autocode_turn(role="player") -> [implement]
    -> autocode_turn(role="coach", execute=true, backend="auto", cwd="<workspace>") -> [independent verify]
    -> autocode_turn(role="advance", coach_feedback=..., approved=false)
           ^                                                            |
           |________________ loop until APPROVED or max_turns __________|
```

## Codex Role Rules

- The current Codex session is always the PLAYER.
- The coach step should be executed through Hegelion, not answered directly in the current session.
- Prefer a separate Codex backend for the coach by using `backend="auto"`.
- If `backend="auto"` falls back to prompt-only output, surface that independent coach execution is unavailable. Do not turn the current session into the coach.
- COACH is authoritative. Run tests. Never self-approve.
