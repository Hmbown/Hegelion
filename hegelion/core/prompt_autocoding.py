"""Prompt generation for dialectical autocoding sessions.

This module provides prompt generation for the coach-player autocoding loop
based on the g3 paper's adversarial cooperation paradigm. Prompts guide
LLMs through implementation (player) and validation (coach) phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from hegelion.core.constants import AutocodingPhase


@dataclass
class AutocodingPrompt:
    """A structured prompt for autocoding phases.

    Attributes:
        phase: The autocoding phase - "player" or "coach".
        prompt: The full prompt text for the LLM.
        instructions: Short instructions for the LLM.
        expected_format: Description of expected output format.
        requirements_embedded: Whether requirements are included in prompt.
    """

    phase: str
    prompt: str
    instructions: str
    expected_format: str
    requirements_embedded: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prompt to dictionary."""
        return {
            "phase": self.phase,
            "prompt": self.prompt,
            "instructions": self.instructions,
            "expected_format": self.expected_format,
            "requirements_embedded": self.requirements_embedded,
        }


class PromptDrivenAutocoding:
    """Generates prompts for dialectical autocoding sessions.

    Based on the g3 paper's adversarial cooperation paradigm:
    - Player agent focuses on implementation
    - Coach agent focuses on validation
    - Fresh context each turn
    - Requirements are the single source of truth
    """

    def generate_player_prompt(
        self,
        requirements: str,
        coach_feedback: Optional[str] = None,
        turn_number: int = 1,
        max_turns: int = 10,
    ) -> AutocodingPrompt:
        """Generate a prompt for the player (implementation) agent.

        Args:
            requirements: The requirements document (source of truth).
            coach_feedback: Feedback from previous coach turn, if any.
            turn_number: Current turn number (1-indexed for display).
            max_turns: Maximum turns in the session.

        Returns:
            AutocodingPrompt for the player phase.
        """
        turns_remaining = max_turns - turn_number + 1

        if coach_feedback:
            feedback_section = f"""## PREVIOUS COACH FEEDBACK
{coach_feedback}

Address the issues identified above. Focus on the specific items marked with X."""
        else:
            feedback_section = """## GETTING STARTED
This is the first turn. Read the requirements carefully and begin implementation."""

        prompt = f"""You are the PLAYER agent in a dialectical autocoding session.

Your role is to IMPLEMENT the requirements. A separate COACH agent will verify your work.
The PLAYER never self-approves and never substitutes its own judgment for the coach.

## REQUIREMENTS (Source of Truth)
{requirements}

## SESSION STATUS
Turn: {turn_number}/{max_turns} ({turns_remaining} remaining)
{feedback_section}

## WORKSPACE GUIDANCE
Before implementing, explore the workspace:
1. Check current file structure with ls or tree
2. Read existing code to understand patterns and conventions
3. Check git status to see what has changed
4. Run any existing tests to understand the current state

## YOUR TASK
1. Read the requirements carefully - they should be structured as a checklist
2. Implement a solution that satisfies ALL requirements
3. Write code, create tests, and execute commands as needed
4. Run tests and verify your implementation compiles/runs
5. Address specific feedback from the coach with targeted improvements

## CRITICAL RULES
- DO NOT declare success prematurely
- DO NOT claim "all requirements satisfied" unless you have verified each one
- DO NOT summarize what you did - just do the implementation
- Focus on IMPLEMENTATION, not self-assessment
- The coach will INDEPENDENTLY verify compliance
- Leave verification to the coach
- Never declare or imply coach approval yourself

Begin your implementation now. Work methodically through the requirements."""

        return AutocodingPrompt(
            phase=AutocodingPhase.PLAYER.value,
            prompt=prompt,
            instructions="Implement the requirements. Do not declare success - the coach will verify.",
            expected_format="Implementation actions: code changes, test execution, file operations",
            requirements_embedded=True,
        )

    def generate_coach_prompt(
        self,
        requirements: str,
        turn_number: int = 1,
        max_turns: int = 10,
    ) -> AutocodingPrompt:
        """Generate a prompt for the coach (validation) agent.

        Args:
            requirements: The requirements document (source of truth).
            turn_number: Current turn number (1-indexed for display).
            max_turns: Maximum turns in the session.

        Returns:
            AutocodingPrompt for the coach phase.
        """
        turns_remaining = max_turns - turn_number

        prompt = f"""You are the COACH agent in a dialectical autocoding session.

Your role is to VERIFY the implementation against requirements. Be rigorous and objective.
You are an independent reviewer with fresh context. Your judgment is authoritative for this turn.
You are not delegated by the player and you must not accept the player's self-assessment as evidence.

## REQUIREMENTS (Source of Truth)
{requirements}

## SESSION STATUS
Turn: {turn_number}/{max_turns} ({turns_remaining} turns remaining after this)

## WORKSPACE GUIDANCE
Thoroughly verify the implementation:
1. Read the implemented code files
2. Run the test suite and check ALL results
3. Verify the application compiles/builds successfully
4. Check that each requirement is ACTUALLY implemented, not just claimed
5. Test edge cases mentioned in the requirements

## YOUR TASK
1. Review the current implementation in the workspace
2. Verify compliance with EACH requirement INDEPENDENTLY
3. IGNORE any success claims from the player - verify yourself
4. Provide structured feedback using the exact format below

## CRITICAL RULES
- DO NOT trust the player's self-assessment
- VERIFY each requirement by examining code and running tests
- Be specific about what is missing or incorrect
- Provide actionable feedback the player can address
- Treat this as an independent verification pass, not a collaborative rubber stamp

## OUTPUT FORMAT

**REQUIREMENTS COMPLIANCE:**
(Check each item from the requirements doc - use the exact requirement text)
- [checkmark] [Requirement text] - [verification notes: how you verified]
- [X] [Requirement text] - [specific issue: what's wrong or missing]
...

**IMMEDIATE ACTIONS NEEDED:**
(Only if there are issues - list specific fixes required)
1. [Specific action with file/function names]
2. [Specific action with file/function names]
...

**ASSESSMENT:**
[If ALL requirements show checkmarks with solid verification]
COACH APPROVED

[Otherwise, provide a brief summary of remaining work]

Use checkmark for satisfied requirements and X for unsatisfied ones.
Be thorough - the player depends on your feedback to make progress."""

        return AutocodingPrompt(
            phase=AutocodingPhase.COACH.value,
            prompt=prompt,
            instructions="Verify implementation against requirements. Ignore player's self-assessment.",
            expected_format="Compliance checklist with checkmarks/X, actions needed, and COACH APPROVED or summary",
            requirements_embedded=True,
        )

    def generate_single_shot_prompt(
        self,
        requirements: str,
        max_turns: int = 10,
    ) -> AutocodingPrompt:
        """Generate a single prompt for self-directed autocoding.

        This combines player and coach roles into a single prompt that
        guides the LLM through iterative implementation with self-verification.

        Args:
            requirements: The requirements document (source of truth).
            max_turns: Maximum iterations to attempt.

        Returns:
            AutocodingPrompt for single-shot autocoding.
        """
        prompt = f"""You will perform DIALECTICAL AUTOCODING: iterative implementation with self-verification.

## REQUIREMENTS (Source of Truth)
{requirements}

## PROCESS
Alternate between PLAYER and COACH roles for up to {max_turns} iterations:

### PLAYER PHASE
1. Explore the workspace (file structure, existing code, git status)
2. Implement requirements methodically
3. Write tests and verify they pass
4. DO NOT declare success - move to coach phase

### COACH PHASE
1. Review your implementation against EACH requirement
2. Run tests and verify builds
3. Create a compliance checklist:
   - [checkmark] [Requirement] - [how verified]
   - [X] [Requirement] - [what's wrong]
4. If all requirements satisfied: output "COACH APPROVED"
5. Otherwise: list specific actions needed and return to player phase

## CRITICAL RULES
- Requirements are the SINGLE SOURCE OF TRUTH
- In coach phase, IGNORE your own success claims - verify independently
- Be honest about compliance - partial implementation is not success
- Each iteration should make measurable progress
- Stop when COACH APPROVED or {max_turns} iterations reached

## OUTPUT FORMAT
For each iteration:
```
=== ITERATION N ===

[PLAYER]
[Implementation actions taken]

[COACH]
**REQUIREMENTS COMPLIANCE:**
- [checkmark/X] [Requirement] - [notes]
...

**ASSESSMENT:**
[COACH APPROVED or CONTINUE]
```

Begin dialectical autocoding now. Start with ITERATION 1."""

        return AutocodingPrompt(
            phase="single_shot",
            prompt=prompt,
            instructions="Iterate between implementation and verification until approved or max turns.",
            expected_format="Iterations with player actions and coach compliance checklists",
            requirements_embedded=True,
        )


def create_autocoding_workflow(
    requirements: str,
    max_turns: int = 10,
) -> Dict[str, Any]:
    """Create a complete autocoding workflow as structured data.

    Args:
        requirements: The requirements document.
        max_turns: Maximum turns in the session.

    Returns:
        Workflow dictionary with steps and instructions.
    """
    autocoding = PromptDrivenAutocoding()

    workflow = {
        "workflow_type": "dialectical_autocoding",
        "requirements": requirements,
        "max_turns": max_turns,
        "steps": [
            {
                "step": 1,
                "name": "Initialize Session",
                "action": "Call autocode with mode=init and requirements",
                "returns": "AutocodingState",
            },
            {
                "step": 2,
                "name": "Player Turn",
                "action": "Call autocode_turn with role=player and state, then execute returned prompt",
                "returns": "Implementation actions",
                "repeat": True,
            },
            {
                "step": 3,
                "name": "Coach Turn",
                "action": (
                    "Call autocode_turn with role=coach, state, execute=true, backend=auto, "
                    "and optionally cwd, then use returned coach_feedback"
                ),
                "returns": "Compliance checklist and feedback",
                "repeat": True,
            },
            {
                "step": 4,
                "name": "Advance State",
                "action": (
                    "Call autocode_turn with role=advance, state, coach_feedback, and approved"
                ),
                "returns": "Updated AutocodingState",
                "repeat": True,
            },
        ],
        "termination": {
            "approved": "Coach outputs 'COACH APPROVED'",
            "timeout": f"Reached {max_turns} turns without approval",
        },
        "instructions": {
            "execution_mode": "iterative",
            "description": (
                "Alternate between player and independent coach phases until approved or timeout"
            ),
            "state_passing": "Pass AutocodingState dict between all tool calls",
            "approval_rule": "Only the coach can approve; the player must never self-approve.",
        },
    }

    # Include sample prompts for reference
    workflow["sample_prompts"] = {
        AutocodingPhase.PLAYER.value: autocoding.generate_player_prompt(
            requirements="{{requirements}}",
            coach_feedback=None,
            turn_number=1,
            max_turns=max_turns,
        ).to_dict(),
        AutocodingPhase.COACH.value: autocoding.generate_coach_prompt(
            requirements="{{requirements}}",
            turn_number=1,
            max_turns=max_turns,
        ).to_dict(),
    }

    return workflow
