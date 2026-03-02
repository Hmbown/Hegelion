# /hegelion

Task: $ARGUMENTS

## Routing

| Task type | MCP call |
|-----------|----------|
| Analysis/decision | `mcp__hegelion__dialectic(query, mode="single_shot", response_style="synthesis_only")` |
| Implementation | `mcp__hegelion__autocode(requirements, mode="workflow")` |

## Autocoding Loop

```
mcp__hegelion__autocode(requirements, mode="init")
    -> autocode_turn(role="player") -> [implement]
    -> autocode_turn(role="coach")  -> [verify]
    -> autocode_turn(role="advance", coach_feedback=..., approved=bool)
           ^                                                    |
           |_________ loop until APPROVED or max_turns ________|
```

COACH is authoritative. Run tests. Never self-approve.
