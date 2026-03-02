"""Tests for dialectical autocoding (g3-style coach-player loop)."""

import json
import pytest
from hegelion.core.autocoding_state import (
    AutocodingState,
    save_session,
    load_session,
)
from hegelion.core.prompt_autocoding import (
    PromptDrivenAutocoding,
    AutocodingPrompt,
    create_autocoding_workflow,
)


class TestAutocodingState:
    """Test the AutocodingState dataclass."""

    def test_create_new_session(self):
        """Test creating a new autocoding session."""
        requirements = "- Build a calculator API\n- Add unit tests"
        state = AutocodingState.create(requirements=requirements)

        assert state.requirements == requirements
        assert state.session_id is not None
        assert len(state.session_id) == 36  # UUID format
        assert state.current_turn == 0
        assert state.max_turns == 10
        assert state.phase == "player"
        assert state.turn_history == []
        assert state.last_coach_feedback is None

    def test_create_with_custom_options(self):
        """Test creating session with custom options."""
        state = AutocodingState.create(
            requirements="test",
            max_turns=5,
            session_name="auth-feature",
        )

        assert state.max_turns == 5
        assert state.session_name == "auth-feature"

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        state = AutocodingState.create(
            requirements="test requirements",
            session_name="release-123",
        )
        state_dict = state.to_dict()

        assert state_dict["session_id"] == state.session_id
        assert state_dict["session_name"] == "release-123"
        assert state_dict["requirements"] == "test requirements"
        assert state_dict["current_turn"] == 0
        assert state_dict["phase"] == "player"
        assert state_dict["schema_version"] == 2

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        original = AutocodingState.create(
            requirements="test",
            session_name="test-session",
        )
        state_dict = original.to_dict()
        restored = AutocodingState.from_dict(state_dict)

        assert restored.session_id == original.session_id
        assert restored.session_name == "test-session"
        assert restored.requirements == original.requirements
        assert restored.phase == original.phase

    def test_from_dict_v1_migration(self):
        """Test v1 dict (with status, quality_scores, etc.) is loaded correctly."""
        v1_dict = {
            "schema_version": 1,
            "session_id": "test-uuid",
            "requirements": "test reqs",
            "phase": "player",
            "status": "active",
            "quality_scores": [0.5, 0.7],
            "approval_threshold": 0.9,
            "current_turn": 2,
            "max_turns": 10,
            "turn_history": [],
            "last_coach_feedback": None,
        }
        state = AutocodingState.from_dict(v1_dict)

        assert state.session_id == "test-uuid"
        assert state.phase == "player"
        assert state.current_turn == 2
        # v1 fields silently ignored
        assert not hasattr(state, "status") or not hasattr(state, "quality_scores")

    def test_from_dict_v1_init_phase_maps_to_player(self):
        """Legacy phase='init' should map to the v2 player phase."""
        state = AutocodingState.from_dict(
            {
                "schema_version": 1,
                "session_id": "legacy-init",
                "requirements": "test reqs",
                "phase": "init",
                "status": "active",
            }
        )

        assert state.phase == "player"

    def test_from_dict_v1_invalid_phase_uses_status_fallback(self):
        """If phase is invalid, legacy status should drive fallback when possible."""
        state = AutocodingState.from_dict(
            {
                "schema_version": 1,
                "session_id": "legacy-timeout",
                "requirements": "test reqs",
                "phase": "unknown",
                "status": "timeout",
            }
        )

        assert state.phase == "timeout"

    def test_advance_to_coach(self):
        """Test advancing from player to coach phase."""
        state = AutocodingState.create(requirements="test")
        assert state.phase == "player"

        new_state = state.advance_to_coach()
        assert new_state.phase == "coach"
        assert new_state.current_turn == 0  # Turn doesn't increment yet
        assert new_state.session_id == state.session_id

    def test_advance_to_coach_wrong_phase(self):
        """Test that advancing to coach from wrong phase raises error."""
        state = AutocodingState.create(requirements="test")
        state = state.advance_to_coach()  # Now in coach phase

        with pytest.raises(ValueError, match="Cannot advance to coach"):
            state.advance_to_coach()

    def test_advance_turn_approved(self):
        """Test advancing turn when coach approves."""
        state = AutocodingState.create(requirements="test")
        state = state.advance_to_coach()

        new_state = state.advance_turn(
            coach_feedback="COACH APPROVED",
            approved=True,
        )

        assert new_state.phase == "approved"
        assert new_state.current_turn == 1
        assert new_state.last_coach_feedback == "COACH APPROVED"

    def test_advance_turn_continue(self):
        """Test advancing turn when coach rejects."""
        state = AutocodingState.create(requirements="test")
        state = state.advance_to_coach()

        new_state = state.advance_turn(
            coach_feedback="Fix the tests",
            approved=False,
        )

        assert new_state.phase == "player"
        assert new_state.current_turn == 1
        assert new_state.last_coach_feedback == "Fix the tests"

    def test_advance_turn_timeout(self):
        """Test timeout when max turns reached."""
        state = AutocodingState.create(requirements="test", max_turns=1)
        state = state.advance_to_coach()

        new_state = state.advance_turn(
            coach_feedback="Still not complete",
            approved=False,
        )

        assert new_state.phase == "timeout"
        assert new_state.current_turn == 1

    def test_is_complete(self):
        """Test completion detection."""
        state = AutocodingState.create(requirements="test")
        assert not state.is_complete()

        state = state.advance_to_coach()
        approved_state = state.advance_turn("OK", approved=True)
        assert approved_state.is_complete()

    def test_turns_remaining(self):
        """Test turns remaining calculation."""
        state = AutocodingState.create(requirements="test", max_turns=5)
        assert state.turns_remaining() == 5

        state = state.advance_to_coach()
        state = state.advance_turn("feedback", approved=False)
        assert state.turns_remaining() == 4

    def test_turn_history_recording(self):
        """Test that turn history is properly recorded."""
        state = AutocodingState.create(requirements="test")
        state = state.advance_to_coach()
        state = state.advance_turn("feedback1", approved=False)

        assert len(state.turn_history) == 1
        assert state.turn_history[0]["turn"] == 0
        assert state.turn_history[0]["feedback"] == "feedback1"
        assert state.turn_history[0]["approved"] is False

    def test_validation_invalid_phase(self):
        """Test validation catches invalid phase."""
        with pytest.raises(ValueError, match="Invalid phase"):
            AutocodingState(
                session_id="test",
                requirements="test",
                phase="invalid_phase",
            )


class TestPromptDrivenAutocoding:
    """Test the prompt generation for autocoding."""

    @pytest.fixture
    def autocoding(self):
        return PromptDrivenAutocoding()

    @pytest.fixture
    def sample_requirements(self):
        return """## Requirements
- [ ] Build a REST API with Express.js
- [ ] Add authentication with JWT
- [ ] Write unit tests with Jest
- [ ] Add input validation
"""

    def test_generate_player_prompt_first_turn(self, autocoding, sample_requirements):
        """Test player prompt on first turn."""
        prompt = autocoding.generate_player_prompt(
            requirements=sample_requirements,
            coach_feedback=None,
            turn_number=1,
            max_turns=10,
        )

        assert isinstance(prompt, AutocodingPrompt)
        assert prompt.phase == "player"
        assert sample_requirements in prompt.prompt
        assert "PLAYER agent" in prompt.prompt
        assert "Turn: 1/10" in prompt.prompt
        assert "first turn" in prompt.prompt.lower()
        assert "DO NOT declare success" in prompt.prompt

    def test_generate_player_prompt_with_feedback(self, autocoding, sample_requirements):
        """Test player prompt with coach feedback."""
        feedback = "Missing JWT validation middleware"
        prompt = autocoding.generate_player_prompt(
            requirements=sample_requirements,
            coach_feedback=feedback,
            turn_number=3,
            max_turns=10,
        )

        assert feedback in prompt.prompt
        assert "Turn: 3/10" in prompt.prompt
        assert "PREVIOUS COACH FEEDBACK" in prompt.prompt

    def test_generate_player_prompt_workspace_guidance(self, autocoding, sample_requirements):
        """Test player prompt includes workspace guidance."""
        prompt = autocoding.generate_player_prompt(
            requirements=sample_requirements,
        )

        assert "WORKSPACE GUIDANCE" in prompt.prompt
        assert "file structure" in prompt.prompt.lower()
        assert "git status" in prompt.prompt.lower()

    def test_generate_coach_prompt(self, autocoding, sample_requirements):
        """Test coach prompt generation."""
        prompt = autocoding.generate_coach_prompt(
            requirements=sample_requirements,
            turn_number=2,
            max_turns=10,
        )

        assert isinstance(prompt, AutocodingPrompt)
        assert prompt.phase == "coach"
        assert sample_requirements in prompt.prompt
        assert "COACH agent" in prompt.prompt
        assert "Turn: 2/10" in prompt.prompt
        assert "IGNORE" in prompt.prompt
        assert "REQUIREMENTS COMPLIANCE" in prompt.prompt
        assert "COACH APPROVED" in prompt.prompt

    def test_generate_coach_prompt_workspace_guidance(self, autocoding, sample_requirements):
        """Test coach prompt includes workspace guidance."""
        prompt = autocoding.generate_coach_prompt(
            requirements=sample_requirements,
        )

        assert "WORKSPACE GUIDANCE" in prompt.prompt
        assert "Run the test suite" in prompt.prompt
        assert "compiles/builds" in prompt.prompt

    def test_generate_single_shot_prompt(self, autocoding, sample_requirements):
        """Test single-shot prompt generation."""
        prompt = autocoding.generate_single_shot_prompt(
            requirements=sample_requirements,
            max_turns=5,
        )

        assert prompt.phase == "single_shot"
        assert sample_requirements in prompt.prompt
        assert "DIALECTICAL AUTOCODING" in prompt.prompt
        assert "PLAYER PHASE" in prompt.prompt
        assert "COACH PHASE" in prompt.prompt
        assert "5 iterations" in prompt.prompt
        assert "COACH APPROVED" in prompt.prompt

    def test_prompt_to_dict(self, autocoding):
        """Test prompt serialization."""
        prompt = autocoding.generate_player_prompt(requirements="test")
        prompt_dict = prompt.to_dict()

        assert prompt_dict["phase"] == "player"
        assert "prompt" in prompt_dict
        assert "instructions" in prompt_dict
        assert "expected_format" in prompt_dict
        assert prompt_dict["requirements_embedded"] is True


class TestAutocodingWorkflow:
    """Test workflow creation helpers."""

    def test_create_autocoding_workflow(self):
        """Test workflow creation."""
        workflow = create_autocoding_workflow(
            requirements="Build a calculator",
            max_turns=5,
        )

        assert workflow["workflow_type"] == "dialectical_autocoding"
        assert workflow["requirements"] == "Build a calculator"
        assert workflow["max_turns"] == 5
        assert len(workflow["steps"]) == 4

        step_names = [s["name"] for s in workflow["steps"]]
        assert "Initialize Session" in step_names
        assert "Player Turn" in step_names
        assert "Coach Turn" in step_names
        assert "Advance State" in step_names

        actions = [s["action"] for s in workflow["steps"]]
        assert actions[0] == "Call autocode with mode=init and requirements"
        assert "autocode_turn with role=player" in actions[1]
        assert "autocode_turn with role=coach" in actions[2]
        assert "autocode_turn with role=advance" in actions[3]

    def test_workflow_termination_conditions(self):
        """Test workflow termination conditions."""
        workflow = create_autocoding_workflow(requirements="test", max_turns=10)

        assert "termination" in workflow
        assert "approved" in workflow["termination"]
        assert "timeout" in workflow["termination"]
        assert "10 turns" in workflow["termination"]["timeout"]

    def test_workflow_sample_prompts(self):
        """Test workflow includes sample prompts."""
        workflow = create_autocoding_workflow(requirements="test")

        assert "sample_prompts" in workflow
        assert "player" in workflow["sample_prompts"]
        assert "coach" in workflow["sample_prompts"]


class TestSessionPersistence:
    """Test session save/load functionality."""

    @pytest.fixture
    def sample_state(self):
        """Create a sample state for testing."""
        return AutocodingState.create(
            requirements="- Build a calculator\n- Add tests",
            max_turns=5,
        )

    def test_save_and_load_session(self, sample_state, tmp_path):
        """Test saving and loading a session."""
        filepath = tmp_path / "session.json"
        save_session(sample_state, str(filepath))

        assert filepath.exists()

        loaded = load_session(str(filepath))
        assert loaded.session_id == sample_state.session_id
        assert loaded.requirements == sample_state.requirements
        assert loaded.phase == sample_state.phase
        assert loaded.max_turns == sample_state.max_turns

    def test_save_creates_parent_directories(self, sample_state, tmp_path):
        """Test that save creates parent directories if needed."""
        filepath = tmp_path / "nested" / "dir" / "session.json"
        save_session(sample_state, str(filepath))

        assert filepath.exists()
        loaded = load_session(str(filepath))
        assert loaded.session_id == sample_state.session_id

    def test_load_file_not_found(self, tmp_path):
        """Test load raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Session file not found"):
            load_session(str(tmp_path / "nonexistent.json"))

    def test_load_invalid_json(self, tmp_path):
        """Test load raises JSONDecodeError for invalid JSON."""
        filepath = tmp_path / "invalid.json"
        filepath.write_text("not valid json {{{")

        with pytest.raises(json.JSONDecodeError):
            load_session(str(filepath))

    def test_save_session_with_history(self, tmp_path):
        """Test saving a session that has turn history."""
        state = AutocodingState.create(requirements="test")
        state = state.advance_to_coach()
        state = state.advance_turn(
            coach_feedback="Needs work",
            approved=False,
        )

        filepath = tmp_path / "session_with_history.json"
        save_session(state, str(filepath))

        loaded = load_session(str(filepath))
        assert len(loaded.turn_history) == 1
        assert loaded.turn_history[0]["feedback"] == "Needs work"
        assert loaded.last_coach_feedback == "Needs work"

    def test_save_and_load_session_with_unicode(self, tmp_path):
        """Test saving and loading session with Unicode content (Windows compatibility)."""
        requirements = """## Requirements
- [ ] Build a REST API with émojis 🚀
- [ ] Add äöü special characters
- [ ] Support 日本語 Japanese text
- [ ] Handle → arrows and • bullets"""
        state = AutocodingState.create(requirements=requirements)
        state = state.advance_to_coach()
        state = state.advance_turn(
            coach_feedback="Missing émoji support 🎉",
            approved=False,
        )

        filepath = tmp_path / "unicode_session.json"
        save_session(state, str(filepath))

        loaded = load_session(str(filepath))
        assert loaded.requirements == requirements
        assert "émojis 🚀" in loaded.requirements
        assert "日本語" in loaded.requirements
        assert "Missing émoji support 🎉" in loaded.last_coach_feedback
