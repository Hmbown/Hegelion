---
name: hegelion
description: Dialectical reasoning and autocoding via Hegelion MCP tools.
---

# Hegelion Skill

## Routing

| Task type | MCP call |
|-----------|----------|
| Analysis/decision | `mcp__hegelion__dialectical_single_shot(query, response_style="synthesis_only")` |
| Implementation | `mcp__hegelion__hegelion(requirements, mode="workflow")` |

Tip: If CLI execution is configured, set `execute=true` on `dialectical_single_shot` to return the final answer in one call.

## Autocoding Loop

```
mcp__hegelion__hegelion(requirements, mode="workflow")
    -> player_prompt -> [implement] -> coach_prompt -> [verify] -> autocoding_advance
           ^                                                            |
           |________________ loop until APPROVED or max_turns __________|
```

COACH is authoritative. Run tests. Never self-approve.
