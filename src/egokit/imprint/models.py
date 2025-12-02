"""Data models for Imprint feature.

Pure Python dataclasses for representing session logs, detected patterns,
and policy suggestions. No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class MessageRole(str, Enum):
    """Role of the message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class PatternConfidence(str, Enum):
    """Confidence level for detected patterns."""

    HIGH = "high"  # 5+ occurrences, explicit corrections
    MEDIUM = "medium"  # 3-4 occurrences
    LOW = "low"  # 2 occurrences


@dataclass
class Message:
    """A single message in a conversation session."""

    role: MessageRole
    content: str
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Ensure role is MessageRole enum."""
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)


@dataclass
class Session:
    """A conversation session with an AI coding assistant."""

    session_id: str
    messages: list[Message]
    source: Literal["claude_code", "augment"]
    project_path: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def user_messages(self) -> list[Message]:
        """Get only user messages from the session."""
        return [m for m in self.messages if m.role == MessageRole.USER]

    @property
    def message_pairs(self) -> list[tuple[Message, Message]]:
        """Get user-assistant message pairs for analysis."""
        pairs: list[tuple[Message, Message]] = []
        for i, msg in enumerate(self.messages):
            if msg.role == MessageRole.USER and i + 1 < len(self.messages):
                next_msg = self.messages[i + 1]
                if next_msg.role == MessageRole.ASSISTANT:
                    pairs.append((msg, next_msg))
        return pairs


@dataclass
class CorrectionPattern:
    """A detected pattern of user corrections."""

    category: str  # e.g., "type_hints", "imports", "docstrings"
    description: str
    occurrences: int
    confidence: PatternConfidence
    evidence: list[str] = field(default_factory=list)  # Actual correction quotes
    sessions: list[str] = field(default_factory=list)  # Session IDs


@dataclass
class StylePreference:
    """A detected style preference from user feedback."""

    preference: str  # e.g., "concise", "verbose", "code_first"
    description: str
    occurrences: int
    confidence: PatternConfidence
    evidence: list[str] = field(default_factory=list)
    sessions: list[str] = field(default_factory=list)  # Session IDs


@dataclass
class ImplicitPattern:
    """An implicit pattern detected from user behavior."""

    pattern_type: str  # e.g., "policy_reference", "tool_preference"
    description: str
    frequency: float  # Percentage of times this occurs
    occurrences: int
    confidence: PatternConfidence
    evidence: list[str] = field(default_factory=list)


@dataclass
class PolicySuggestion:
    """A suggested policy based on detected patterns."""

    suggested_id: str  # e.g., "STYLE-001"
    severity: Literal["critical", "required", "recommended", "info"]
    description: str
    rationale: str
    example: str | None = None
    example_violation: str | None = None
    source_pattern: CorrectionPattern | StylePreference | ImplicitPattern | None = None


@dataclass
class ImprintReport:
    """Complete imprint analysis report."""

    sessions_analyzed: int
    claude_sessions: int
    augment_sessions: int
    date_range_start: datetime | None
    date_range_end: datetime | None
    correction_patterns: list[CorrectionPattern] = field(default_factory=list)
    style_preferences: list[StylePreference] = field(default_factory=list)
    implicit_patterns: list[ImplicitPattern] = field(default_factory=list)
    policy_suggestions: list[PolicySuggestion] = field(default_factory=list)

    @property
    def has_patterns(self) -> bool:
        """Check if any patterns were detected."""
        return bool(
            self.correction_patterns
            or self.style_preferences
            or self.implicit_patterns,
        )

