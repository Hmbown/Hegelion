"""Tests for model-agnostic prompt generation."""

import pytest
from hegelion.core.prompt_dialectic import (
    PromptDrivenDialectic,
    DialecticalPrompt,
    create_dialectical_workflow,
    create_single_shot_dialectic_prompt,
)


class TestPromptDrivenDialectic:
    """Test the prompt generation logic."""

    @pytest.fixture
    def dialectic(self):
        return PromptDrivenDialectic()

    def test_generate_thesis_prompt(self, dialectic):
        """Test thesis prompt generation."""
        query = "Is AI conscious?"
        prompt = dialectic.generate_thesis_prompt(query)

        assert isinstance(prompt, DialecticalPrompt)
        assert prompt.phase == "thesis"
        assert query in prompt.prompt
        assert "THESIS phase" in prompt.prompt
        assert "uncertainty" in prompt.prompt

    def test_generate_antithesis_prompt(self, dialectic):
        """Test antithesis prompt generation."""
        query = "Is AI conscious?"
        thesis = "AI mimics consciousness but lacks subjective experience."

        prompt = dialectic.generate_antithesis_prompt(query, thesis)

        assert isinstance(prompt, DialecticalPrompt)
        assert prompt.phase == "antithesis"
        assert query in prompt.prompt
        assert thesis in prompt.prompt
        assert "search tools" not in prompt.prompt

    def test_generate_antithesis_with_search(self, dialectic):
        """Test antithesis prompt with search instructions."""
        query = "Is AI conscious?"
        thesis = "AI mimics consciousness."

        prompt = dialectic.generate_antithesis_prompt(query, thesis, use_search_context=True)

        assert "search tools" in prompt.prompt
        assert "recent developments" in prompt.prompt

    def test_generate_council_prompts(self, dialectic):
        """Test council prompt generation."""
        query = "Is AI conscious?"
        thesis = "AI mimics consciousness."

        prompts = dialectic.generate_council_prompts(query, thesis)

        assert len(prompts) == 3
        phases = [p.phase for p in prompts]
        assert "council_the_logician" in phases
        assert "council_the_empiricist" in phases
        assert "council_the_ethicist" in phases

        for p in prompts:
            assert query in p.prompt
            assert thesis in p.prompt

    def test_generate_synthesis_prompt(self, dialectic):
        """Test synthesis prompt generation."""
        query = "Q"
        thesis = "T"
        antithesis = "A"

        prompt = dialectic.generate_synthesis_prompt(query, thesis, antithesis)

        assert prompt.phase == "synthesis"
        assert query in prompt.prompt
        assert thesis in prompt.prompt
        assert antithesis in prompt.prompt
        assert "TRANSCENDS" in prompt.prompt

    def test_generate_synthesis_with_contradictions(self, dialectic):
        """Test synthesis prompt with explicit contradictions."""
        contradictions = ["C1", "C2"]
        prompt = dialectic.generate_synthesis_prompt("Q", "T", "A", contradictions=contradictions)

        assert "C1" in prompt.prompt
        assert "C2" in prompt.prompt


class TestWorkflowHelpers:
    """Test high-level workflow helpers."""

    def test_create_dialectical_workflow_basic(self):
        """Test basic workflow creation."""
        workflow = create_dialectical_workflow("test query")

        assert workflow["query"] == "test query"
        assert len(workflow["steps"]) == 3  # Thesis, Antithesis, Synthesis

        step_names = [s["name"] for s in workflow["steps"]]
        assert "Generate Thesis" in step_names
        assert "Generate Antithesis" in step_names
        assert "Generate Synthesis" in step_names

    def test_create_dialectical_workflow_with_council(self):
        """Test workflow with council."""
        workflow = create_dialectical_workflow("test", use_council=True)

        step_names = [s["name"] for s in workflow["steps"]]
        assert "Generate Thesis" in step_names
        assert any("Council Critique" in name for name in step_names)
        # Thesis + 3 Council + Synthesis = 5 steps
        assert len(workflow["steps"]) == 5

        # Verify synthesis step references all council members
        synthesis_step = workflow["steps"][-1]
        assert synthesis_step["name"] == "Generate Synthesis"
        synthesis_prompt_text = synthesis_step["prompt"]["prompt"]

        # It should contain references to all council members variables
        # Note: step numbers for council are 2, 3, 4
        assert "### Council The Logician" in synthesis_prompt_text
        assert "{{council_the_logician_from_step_2}}" in synthesis_prompt_text
        assert "### Council The Empiricist" in synthesis_prompt_text
        assert "{{council_the_empiricist_from_step_3}}" in synthesis_prompt_text
        assert "### Council The Ethicist" in synthesis_prompt_text
        assert "{{council_the_ethicist_from_step_4}}" in synthesis_prompt_text

    def test_single_shot_prompt(self):
        """Test single shot prompt generation."""
        prompt = create_single_shot_dialectic_prompt(
            "test query", use_search=True, use_council=True
        )

        assert "test query" in prompt
        assert "THESIS" in prompt
        assert "ANTITHESIS" in prompt
        assert "SYNTHESIS" in prompt
        assert "search tools" in prompt
        assert "THE LOGICIAN" in prompt

    def test_single_shot_json_prompt_is_consistent(self):
        """JSON style should avoid conflicting text-only formats."""
        prompt = create_single_shot_dialectic_prompt("test query", response_style="json")

        assert "Return ONLY a JSON object" in prompt
        assert "CONTRADICTION:" not in prompt
        assert "RESEARCH_PROPOSAL:" not in prompt
