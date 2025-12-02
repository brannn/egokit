"""Pattern detection for Imprint feature.

Heuristic-based detection of correction patterns, style preferences,
and implicit behavioral patterns from AI session logs.

No ML, no embeddings - pure regex and frequency analysis.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .models import (
    CorrectionPattern,
    ImplicitPattern,
    PatternConfidence,
    Session,
    StylePreference,
)

# Correction indicator patterns - phrases that suggest user is correcting AI
CORRECTION_INDICATORS = [
    r"(?i)^no[,.]?\s",  # "No, I meant..."
    r"(?i)^actually[,.]?\s",  # "Actually, use..."
    r"(?i)^that'?s?\s+not\s+(right|correct|what)",  # "That's not right"
    r"(?i)^i\s+said\s+to",  # "I said to..."
    r"(?i)^don'?t\s+(?:do|use)",  # "Don't do X"
    r"(?i)^use\s+\w+\s+(?:not|instead)",  # "Use X not Y"
    r"(?i)^not\s+\w+[,]\s*(?:use|try)",  # "Not X, use Y"
    r"(?i)^please\s+(?:don'?t|stop)",  # "Please don't..."
    r"(?i)^i\s+(?:wanted|meant|asked)",  # "I wanted/meant/asked..."
    r"(?i)^wrong[,.]",  # "Wrong, ..."
    r"(?i)^nope[,.]",  # "Nope, ..."
]

# Style preference patterns - meta-comments about AI behavior
# These should only match actual user preferences, not system context
STYLE_PATTERNS = {
    "concise": [
        r"(?i)^be\s+(?:more\s+)?concise",
        r"(?i)^too\s+(?:verbose|long|wordy)",
        r"(?i)shorter\s+(?:response|answer|explanation)",
        r"(?i)skip\s+(?:the\s+)?explanation",
        r"(?i)^just\s+(?:show|give)\s+(?:me\s+)?(?:the\s+)?code",
        r"(?i)keep\s+it\s+(?:short|brief)",
    ],
    "verbose": [
        r"(?i)^(?:i\s+need\s+)?more\s+detail",
        r"(?i)^explain\s+(?:this\s+)?(?:more|further|better)",
        r"(?i)^too\s+brief",
        r"(?i)^can\s+you\s+elaborate",
        r"(?i)^please\s+explain",
        r"(?i)^i\s+don'?t\s+understand",
    ],
    "code_first": [
        r"(?i)show\s+(?:me\s+)?(?:the\s+)?code\s+first",
        r"(?i)code\s+before\s+explanation",
        r"(?i)^start\s+with\s+(?:the\s+)?code",
    ],
}

# Patterns to filter out system-injected content (not real user messages)
SYSTEM_NOISE_PATTERNS = [
    r"^<supervisor>",
    r"^<user>",
    r"^<agent",
    r"^\s*#\s*(?:AGENTS|Policy|EgoKit)",
    r"^\s*<!--",
]

# Policy reference patterns - mentions of policy IDs
POLICY_ID_PATTERN = re.compile(r"\b([A-Z]{2,6}-\d{3})\b")


# Maximum evidence examples to keep per pattern
MAX_EVIDENCE_EXAMPLES = 5


@dataclass
class DetectorConfig:
    """Configuration for pattern detection."""

    min_occurrences_high: int = 5  # Minimum for high confidence
    min_occurrences_medium: int = 3  # Minimum for medium confidence
    min_occurrences_low: int = 2  # Minimum for any detection
    implicit_pattern_threshold: float = 0.6  # 60% frequency for implicit patterns


class PatternDetector:
    """Detects patterns in AI session logs.

    Analyzes user messages to find:
    1. Explicit corrections (user telling AI it got something wrong)
    2. Style preferences (user requesting behavior changes)
    3. Implicit patterns (repeated behaviors that suggest preferences)
    4. Policy references (mentions of policy IDs)
    """

    def __init__(self, config: DetectorConfig | None = None) -> None:
        """Initialize the pattern detector.

        Args:
            config: Detection configuration, uses defaults if not provided
        """
        self.config = config or DetectorConfig()
        self._correction_patterns = [re.compile(p) for p in CORRECTION_INDICATORS]
        self._style_patterns = {
            category: [re.compile(p) for p in patterns]
            for category, patterns in STYLE_PATTERNS.items()
        }
        self._noise_patterns = [re.compile(p) for p in SYSTEM_NOISE_PATTERNS]

    def _is_system_noise(self, text: str) -> bool:
        """Check if message appears to be system-injected content, not real user input."""
        return any(pattern.search(text) for pattern in self._noise_patterns)

    def _get_user_content(self, sessions: list[Session]) -> list[tuple[str, str]]:
        """Extract real user messages, filtering out system noise.

        Returns:
            List of (content, session_id) tuples
        """
        results: list[tuple[str, str]] = []
        for session in sessions:
            for msg in session.user_messages:
                if not self._is_system_noise(msg.content):
                    results.append((msg.content, session.session_id))
        return results

    def detect_corrections(self, sessions: list[Session]) -> list[CorrectionPattern]:
        """Detect correction patterns from sessions.

        Args:
            sessions: List of parsed sessions to analyze

        Returns:
            List of detected correction patterns
        """
        corrections: list[tuple[str, str, str]] = []  # (category, quote, session_id)

        for content, session_id in self._get_user_content(sessions):
            if self._is_correction(content):
                category = self._categorize_correction(content)
                # Take first 200 chars as evidence quote
                quote = content[:200].strip()
                corrections.append((category, quote, session_id))

        return self._aggregate_corrections(corrections)

    def _is_correction(self, text: str) -> bool:
        """Check if a message appears to be a correction."""
        return any(pattern.search(text) for pattern in self._correction_patterns)

    def _categorize_correction(self, text: str) -> str:
        """Categorize a correction into a topic area."""
        text_lower = text.lower()

        # Category keywords mapping
        categories = {
            "type_hints": ["type", "typing", "hint", "annotation", "list[", "dict["],
            "imports": ["import", "from ", "module"],
            "docstrings": ["docstring", "documentation", "google style", "numpy style"],
            "naming": ["name", "naming", "snake_case", "camelcase", "variable"],
            "testing": ["test", "testing", "pytest", "unittest"],
            "formatting": ["format", "indent", "spacing", "line length"],
        }

        for category, keywords in categories.items():
            if any(term in text_lower for term in keywords):
                return category

        return "general"

    def _aggregate_corrections(
        self,
        corrections: list[tuple[str, str, str]],
    ) -> list[CorrectionPattern]:
        """Aggregate raw corrections into patterns."""
        by_category: dict[str, list[tuple[str, str]]] = {}
        for category, quote, session_id in corrections:
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((quote, session_id))

        patterns: list[CorrectionPattern] = []
        for category, items in by_category.items():
            count = len(items)
            if count < self.config.min_occurrences_low:
                continue

            confidence = self._get_confidence(count)
            unique_sessions = list({sid for _, sid in items})
            evidence = [quote for quote, _ in items[:5]]  # Keep up to 5 examples

            patterns.append(CorrectionPattern(
                category=category,
                description=f"Corrections about {category.replace('_', ' ')}",
                occurrences=count,
                confidence=confidence,
                evidence=evidence,
                sessions=unique_sessions,
            ))

        return sorted(patterns, key=lambda p: p.occurrences, reverse=True)

    def _get_confidence(self, count: int) -> PatternConfidence:
        """Determine confidence level based on occurrence count."""
        if count >= self.config.min_occurrences_high:
            return PatternConfidence.HIGH
        if count >= self.config.min_occurrences_medium:
            return PatternConfidence.MEDIUM
        return PatternConfidence.LOW

    def detect_style_preferences(
        self,
        sessions: list[Session],
    ) -> list[StylePreference]:
        """Detect style preference patterns from sessions.

        Args:
            sessions: List of parsed sessions to analyze

        Returns:
            List of detected style preferences
        """
        preferences: dict[str, list[tuple[str, str]]] = {}  # category -> [(quote, session_id)]

        for content, session_id in self._get_user_content(sessions):
            for category, patterns in self._style_patterns.items():
                for pattern in patterns:
                    if pattern.search(content):
                        if category not in preferences:
                            preferences[category] = []
                        quote = content[:200].strip()
                        preferences[category].append((quote, session_id))
                        break  # Only count once per category per message

        results: list[StylePreference] = []
        for category, items in preferences.items():
            count = len(items)
            if count < self.config.min_occurrences_low:
                continue

            confidence = self._get_confidence(count)
            unique_sessions = list({sid for _, sid in items})
            evidence = [quote for quote, _ in items[:5]]

            results.append(StylePreference(
                preference=category,
                description=self._style_description(category),
                occurrences=count,
                confidence=confidence,
                evidence=evidence,
                sessions=unique_sessions,
            ))

        return sorted(results, key=lambda p: p.occurrences, reverse=True)

    def _style_description(self, category: str) -> str:
        """Generate a descriptive explanation for a style preference."""
        descriptions = {
            "concise": "Keep responses brief and focused on essential information",
            "verbose": "Provide detailed explanations with context and rationale",
            "code_first": "Show code examples before explanations",
        }
        return descriptions.get(category, f"Preference for {category.replace('_', ' ')} style")

    def detect_implicit_patterns(
        self,
        sessions: list[Session],
    ) -> list[ImplicitPattern]:
        """Detect implicit behavioral patterns from sessions.

        Looks for repeated behaviors that suggest preferences even without
        explicit correction language.

        Args:
            sessions: List of parsed sessions to analyze

        Returns:
            List of detected implicit patterns
        """
        # Track policy ID mentions (only from real user content)
        policy_mentions: Counter[str] = Counter()
        policy_evidence: dict[str, list[str]] = {}

        for content, _session_id in self._get_user_content(sessions):
            for match in POLICY_ID_PATTERN.finditer(content):
                policy_id = match.group(1)
                policy_mentions[policy_id] += 1
                if policy_id not in policy_evidence:
                    policy_evidence[policy_id] = []
                if len(policy_evidence[policy_id]) < MAX_EVIDENCE_EXAMPLES:
                    policy_evidence[policy_id].append(content[:200].strip())

        patterns: list[ImplicitPattern] = []

        # Convert policy mentions to patterns
        for policy_id, count in policy_mentions.items():
            if count < self.config.min_occurrences_low:
                continue

            patterns.append(ImplicitPattern(
                pattern_type="policy_reference",
                description=f"User references policy {policy_id} - consider reinforcing",
                frequency=count / len(sessions) if sessions else 0.0,
                occurrences=count,
                confidence=self._get_confidence(count),
                evidence=policy_evidence.get(policy_id, []),
            ))

        return sorted(patterns, key=lambda p: p.occurrences, reverse=True)

    def detect_all(
        self,
        sessions: list[Session],
    ) -> tuple[list[CorrectionPattern], list[StylePreference], list[ImplicitPattern]]:
        """Run all detection methods on sessions.

        Args:
            sessions: List of parsed sessions to analyze

        Returns:
            Tuple of (corrections, style_preferences, implicit_patterns)
        """
        corrections = self.detect_corrections(sessions)
        style_prefs = self.detect_style_preferences(sessions)
        implicit = self.detect_implicit_patterns(sessions)

        return corrections, style_prefs, implicit
