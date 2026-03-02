"""Tests for the response styles in Hegelion."""

import pytest
from hegelion.core.prompt_dialectic import create_single_shot_dialectic_prompt


class TestResponseStyles:
    """Test suite for response styles functionality."""

    def test_json_style_unchanged(self):
        """Test that json style still works as before."""
        prompt = create_single_shot_dialectic_prompt(
            query="Test query for json style", response_style="json"
        )

        # Check for JSON-specific instructions
        assert '"query":' in prompt
        assert '"thesis":' in prompt
        assert '"antithesis":' in prompt
        assert '"synthesis":' in prompt
        assert "No markdown, no commentary outside the JSON" in prompt

    def test_sections_style_unchanged(self):
        """Test that sections style still works as before."""
        prompt = create_single_shot_dialectic_prompt(
            query="Test query for sections style", response_style="sections"
        )

        # Should use default formatting with sections
        assert "## THESIS" in prompt
        assert "## ANTITHESIS" in prompt
        assert "## SYNTHESIS" in prompt

    def test_synthesis_only_style_unchanged(self):
        """Test that synthesis_only style still works as before."""
        prompt = create_single_shot_dialectic_prompt(
            query="Test query for synthesis only style", response_style="synthesis_only"
        )

        # Should only include synthesis
        assert "Return ONLY the SYNTHESIS as 2-3 tight paragraphs" in prompt
        assert "Do not include thesis, antithesis, headings, or lists" in prompt

    def test_invalid_response_style(self):
        """Test that invalid response style uses default formatting."""
        prompt = create_single_shot_dialectic_prompt(
            query="Test query", response_style="invalid_style"
        )
        assert "Test query" in prompt
        assert "## THESIS" in prompt

    @pytest.mark.parametrize(
        "style",
        ["json", "sections", "synthesis_only"],
    )
    def test_all_styles_include_core_content(self, style):
        """Test that all styles include the core query content."""
        prompt = create_single_shot_dialectic_prompt(
            query="Test query with specific content: 12345", response_style=style
        )

        assert "Test query with specific content: 12345" in prompt


if __name__ == "__main__":
    pytest.main([__file__])
