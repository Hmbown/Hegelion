---
name: hegelion
description: Dialectical reasoning and autocoding via Hegelion MCP tools.
---

# Hegelion Skill

## Routing

| Task type | MCP call |
|-----------|----------|
| Analysis/decision | `mcp__hegelion__dialectic(query, mode="single_shot", response_style="synthesis_only")` |
| Implementation | `mcp__hegelion__autocode(requirements, mode="workflow")` |

Tip: If CLI execution is configured, set `execute=true` on `dialectic` mode=single_shot to return the final answer in one call.

## Autocoding Loop

```
mcp__hegelion__autocode(requirements, mode="init")
    -> autocode_turn(role="player") -> [implement]
    -> autocode_turn(role="coach") -> [verify]
    -> autocode_turn(role="advance", coach_feedback=..., approved=false)
           ^                                                            |
           |________________ loop until APPROVED or max_turns __________|
```

COACH is authoritative. Run tests. Never self-approve.
