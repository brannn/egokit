"""Tests for EgoKit Imprint feature.

Tests cover:
- Log parsers (Claude Code JSONL, Augment JSON)
- Pattern detection (corrections, style preferences, implicit patterns)
- Policy suggestion generation
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from egokit.imprint import (
    AugmentParser,
    ClaudeCodeParser,
    CorrectionPattern,
    Message,
    MessageRole,
    PatternConfidence,
    PatternDetector,
    PolicySuggester,
    Session,
    StylePreference,
    SuggesterConfig,
)


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self) -> None:
        """Test creating a basic message."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.timestamp is None

    def test_message_with_timestamp(self) -> None:
        """Test message with timestamp."""
        ts = datetime.now(tz=UTC)
        msg = Message(role=MessageRole.ASSISTANT, content="Hi", timestamp=ts)
        assert msg.timestamp == ts


class TestSession:
    """Tests for Session dataclass."""

    def test_session_creation(self) -> None:
        """Test creating a session with messages."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
            Message(role=MessageRole.USER, content="Help me"),
        ]
        session = Session(
            session_id="test-123",
            messages=messages,
            source="test",
        )
        assert session.session_id == "test-123"
        assert len(session.messages) == 3

    def test_user_messages_property(self) -> None:
        """Test user_messages property filters correctly."""
        messages = [
            Message(role=MessageRole.USER, content="User 1"),
            Message(role=MessageRole.ASSISTANT, content="Assistant 1"),
            Message(role=MessageRole.USER, content="User 2"),
        ]
        session = Session(session_id="test", messages=messages, source="test")
        user_msgs = session.user_messages
        assert len(user_msgs) == 2
        assert all(m.role == MessageRole.USER for m in user_msgs)


class TestClaudeCodeParser:
    """Tests for Claude Code JSONL parser."""

    def test_discover_finds_jsonl_files(self, tmp_path: Path) -> None:
        """Test that discover finds .jsonl files."""
        # Create test structure
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        (project_dir / "session1.jsonl").write_text("{}\n")
        (project_dir / "session2.jsonl").write_text("{}\n")
        (project_dir / "other.txt").write_text("not a log")

        parser = ClaudeCodeParser()
        files = parser.discover(tmp_path / "projects")
        assert len(files) == 2
        assert all(f.suffix == ".jsonl" for f in files)

    def test_parse_user_message(self, tmp_path: Path) -> None:
        """Test parsing a user message from JSONL."""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text(
            json.dumps({"type": "human", "message": {"content": "Hello Claude"}}) + "\n",
        )

        parser = ClaudeCodeParser()
        sessions = list(parser.parse(log_file))
        assert len(sessions) == 1
        assert len(sessions[0].messages) == 1
        assert sessions[0].messages[0].role == MessageRole.USER
        assert sessions[0].messages[0].content == "Hello Claude"

    def test_parse_assistant_message(self, tmp_path: Path) -> None:
        """Test parsing an assistant message from JSONL."""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text(
            json.dumps({"type": "assistant", "message": {"content": "Hello!"}}) + "\n",
        )

        parser = ClaudeCodeParser()
        sessions = list(parser.parse(log_file))
        assert len(sessions) == 1
        assert sessions[0].messages[0].role == MessageRole.ASSISTANT

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty JSONL file."""
        log_file = tmp_path / "empty.jsonl"
        log_file.write_text("")

        parser = ClaudeCodeParser()
        sessions = list(parser.parse(log_file))
        assert len(sessions) == 0

    def test_parse_malformed_json(self, tmp_path: Path) -> None:
        """Test that malformed JSON lines are skipped."""
        log_file = tmp_path / "malformed.jsonl"
        log_file.write_text("not json\n" + json.dumps({"type": "human", "message": {"content": "Valid"}}) + "\n")

        parser = ClaudeCodeParser()
        sessions = list(parser.parse(log_file))
        assert len(sessions) == 1
        assert sessions[0].messages[0].content == "Valid"


class TestAugmentParser:
    """Tests for Augment JSON parser."""

    def test_discover_validates_augment_format(self, tmp_path: Path) -> None:
        """Test that discover only finds valid Augment exports."""
        # Valid Augment export (nested format)
        valid_file = tmp_path / "export_2025-01-01.json"
        valid_file.write_text(json.dumps({
            "conversation": {"chatHistory": []},
        }))

        # Invalid file (no chatHistory)
        invalid_file = tmp_path / "other_2025-01-01.json"
        invalid_file.write_text(json.dumps({"data": []}))

        parser = AugmentParser()
        files = parser.discover(tmp_path)
        assert len(files) == 1
        assert files[0] == valid_file

    def test_parse_nested_chat_history(self, tmp_path: Path) -> None:
        """Test parsing Augment export with nested conversation.chatHistory."""
        export_file = tmp_path / "export.json"
        export_file.write_text(json.dumps({
            "conversation": {
                "chatHistory": [
                    {
                        "request_message": "Help me code",
                        "response_text": "Sure, here's some code",
                        "timestamp": "2025-01-01T10:00:00Z",
                    },
                ],
            },
        }))

        parser = AugmentParser()
        sessions = list(parser.parse(export_file))
        assert len(sessions) == 1
        assert len(sessions[0].messages) == 2
        assert sessions[0].messages[0].role == MessageRole.USER
        assert sessions[0].messages[0].content == "Help me code"
        assert sessions[0].messages[1].role == MessageRole.ASSISTANT

    def test_parse_root_level_chat_history(self, tmp_path: Path) -> None:
        """Test parsing Augment export with root-level chatHistory."""
        export_file = tmp_path / "export.json"
        export_file.write_text(json.dumps({
            "chatHistory": [
                {
                    "request_message": "Question",
                    "response_text": "Answer",
                },
            ],
        }))

        parser = AugmentParser()
        sessions = list(parser.parse(export_file))
        assert len(sessions) == 1
        assert len(sessions[0].messages) == 2

    def test_parse_skips_delimiter_entries(self, tmp_path: Path) -> None:
        """Test that delimiter entries without messages are skipped."""
        export_file = tmp_path / "export.json"
        export_file.write_text(json.dumps({
            "chatHistory": [
                {"chatItemType": "agentic-checkpoint-delimiter"},
                {"request_message": "Real message", "response_text": "Response"},
            ],
        }))

        parser = AugmentParser()
        sessions = list(parser.parse(export_file))
        assert len(sessions) == 1
        assert len(sessions[0].messages) == 2  # Only the real message pair


class TestPatternDetector:
    """Tests for pattern detection."""

    def _make_session(self, user_messages: list[str]) -> Session:
        """Helper to create a session with user messages."""
        messages = []
        for msg in user_messages:
            messages.append(Message(role=MessageRole.USER, content=msg))
            messages.append(Message(role=MessageRole.ASSISTANT, content="OK"))
        return Session(session_id="test", messages=messages, source="test")

    def test_detect_correction_no_pattern(self) -> None:
        """Test that non-corrections aren't detected."""
        session = self._make_session(["Hello", "Thanks", "Good work"])
        detector = PatternDetector()
        corrections = detector.detect_corrections([session])
        assert len(corrections) == 0

    def test_detect_correction_no_prefix(self) -> None:
        """Test detecting 'No, ...' correction."""
        session = self._make_session([
            "No, I meant use Python not JavaScript",
            "No, that's wrong",
        ])
        detector = PatternDetector()
        corrections = detector.detect_corrections([session])
        assert len(corrections) == 1
        assert corrections[0].occurrences == 2

    def test_detect_correction_actually(self) -> None:
        """Test detecting 'Actually, ...' correction."""
        # Need 2+ occurrences to meet min_occurrences_low threshold
        session = self._make_session([
            "Actually, use tabs not spaces",
            "Actually, that's wrong too",
        ])
        detector = PatternDetector()
        corrections = detector.detect_corrections([session])
        assert len(corrections) == 1
        assert corrections[0].occurrences == 2

    def test_detect_correction_category_type_hints(self) -> None:
        """Test that type-related corrections are categorized."""
        session = self._make_session([
            "No, add type hints please",
            "Actually, the type annotation is wrong",
        ])
        detector = PatternDetector()
        corrections = detector.detect_corrections([session])
        assert len(corrections) == 1
        assert corrections[0].category == "type_hints"

    def test_filters_system_noise(self) -> None:
        """Test that system-injected content is filtered out."""
        session = self._make_session([
            "<supervisor>No, this is system context</supervisor>",
            "No, do it differently",  # Real correction
            "No, still wrong",  # Another real correction
        ])
        detector = PatternDetector()
        corrections = detector.detect_corrections([session])
        # Should only detect the 2 real corrections, not the supervisor tag
        assert len(corrections) == 1
        assert corrections[0].occurrences == 2
        # Evidence should not contain supervisor content
        for evidence in corrections[0].evidence:
            assert "supervisor" not in evidence.lower()

    def test_detect_style_concise(self) -> None:
        """Test detecting concise style preference."""
        session = self._make_session([
            "Be more concise please",
            "Too verbose, shorter please",
        ])
        detector = PatternDetector()
        prefs = detector.detect_style_preferences([session])
        assert len(prefs) == 1
        assert prefs[0].preference == "concise"
        assert prefs[0].occurrences == 2

    def test_detect_style_code_first(self) -> None:
        """Test detecting code-first preference."""
        # Need 2+ occurrences to meet min_occurrences_low threshold
        session = self._make_session([
            "show code first please",
            "Show me the code first",
        ])
        detector = PatternDetector()
        prefs = detector.detect_style_preferences([session])
        assert len(prefs) == 1
        assert prefs[0].preference == "code_first"
        assert prefs[0].occurrences == 2

    def test_detect_implicit_policy_reference(self) -> None:
        """Test detecting policy ID references."""
        session = self._make_session([
            "Remember to follow SEC-001",
            "This violates SEC-001 again",
            "SEC-001 is important",
        ])
        detector = PatternDetector()
        implicit = detector.detect_implicit_patterns([session])
        assert len(implicit) == 1
        assert "SEC-001" in implicit[0].description
        assert implicit[0].occurrences == 3

    def test_detect_all_returns_tuple(self) -> None:
        """Test detect_all returns all pattern types."""
        session = self._make_session([
            "No, use Python",
            "Be concise",
            "Follow SEC-001",
        ])
        detector = PatternDetector()
        corrections, styles, implicit = detector.detect_all([session])
        assert isinstance(corrections, list)
        assert isinstance(styles, list)
        assert isinstance(implicit, list)


class TestPolicySuggester:
    """Tests for policy suggestion generation."""

    def test_suggestion_from_correction(self) -> None:
        """Test generating suggestion from correction pattern."""
        correction = CorrectionPattern(
            category="type_hints",
            description="Corrections about type hints",
            occurrences=5,
            confidence=PatternConfidence.HIGH,
            evidence=["No, add type hints"],
            sessions=["session1"],
        )
        suggester = PolicySuggester()
        suggestions = suggester.generate_suggestions([correction], [], [])
        assert len(suggestions) == 1
        assert suggestions[0].severity == "required"  # HIGH -> required
        assert "type hint" in suggestions[0].description.lower()

    def test_suggestion_from_style(self) -> None:
        """Test generating suggestion from style preference."""
        pref = StylePreference(
            preference="concise",
            description="Preference for concise style",
            occurrences=3,
            confidence=PatternConfidence.MEDIUM,
            evidence=["Be concise"],
            sessions=["session1"],
        )
        suggester = PolicySuggester()
        suggestions = suggester.generate_suggestions([], [pref], [])
        assert len(suggestions) == 1
        assert suggestions[0].severity == "recommended"  # MEDIUM -> recommended

    def test_policy_reference_not_suggested(self) -> None:
        """Test that policy references don't generate new suggestions."""
        from egokit.imprint import ImplicitPattern

        pattern = ImplicitPattern(
            pattern_type="policy_reference",
            description="User references policy SEC-001",
            frequency=0.5,
            occurrences=5,
            confidence=PatternConfidence.HIGH,
            evidence=["Follow SEC-001"],
        )
        suggester = PolicySuggester()
        suggestions = suggester.generate_suggestions([], [], [pattern])
        assert len(suggestions) == 0  # Policy references shouldn't create new rules

    def test_to_yaml_snippet(self) -> None:
        """Test YAML snippet generation."""
        from egokit.imprint import PolicySuggestion

        suggestion = PolicySuggestion(
            suggested_id="QUAL-001",
            severity="required",
            description="Use type hints",
            rationale="Detected 5 instances",
            example="No, add type hints",
            source_pattern=None,
        )
        suggester = PolicySuggester()
        yaml = suggester.to_yaml_snippet(suggestion)
        assert "id: QUAL-001" in yaml
        assert "severity: required" in yaml
        assert "description: Use type hints" in yaml
        assert "example:" in yaml

    def test_confidence_filtering(self) -> None:
        """Test that min_confidence filters suggestions."""
        correction_low = CorrectionPattern(
            category="general",
            description="Low confidence",
            occurrences=2,
            confidence=PatternConfidence.LOW,
            evidence=["test"],
            sessions=["s1"],
        )
        correction_high = CorrectionPattern(
            category="general",
            description="High confidence",
            occurrences=10,
            confidence=PatternConfidence.HIGH,
            evidence=["test"],
            sessions=["s1"],
        )

        config = SuggesterConfig(min_confidence=PatternConfidence.HIGH)
        suggester = PolicySuggester(config)
        suggestions = suggester.generate_suggestions([correction_low, correction_high], [], [])
        assert len(suggestions) == 1
        assert suggestions[0].description == "Follow project coding conventions"

    def test_max_suggestions_limit(self) -> None:
        """Test that max_suggestions limits output."""
        corrections = [
            CorrectionPattern(
                category="general",
                description=f"Pattern {i}",
                occurrences=5,
                confidence=PatternConfidence.HIGH,
                evidence=["test"],
                sessions=["s1"],
            )
            for i in range(15)
        ]
        config = SuggesterConfig(max_suggestions=5)
        suggester = PolicySuggester(config)
        suggestions = suggester.generate_suggestions(corrections, [], [])
        assert len(suggestions) == 5

