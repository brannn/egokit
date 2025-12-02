"""Policy suggestion generation for Imprint feature.

Maps detected patterns to charter.yaml structure and generates
rule suggestions with rationale and evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import (
    CorrectionPattern,
    ImplicitPattern,
    PatternConfidence,
    PolicySuggestion,
    StylePreference,
)

if TYPE_CHECKING:
    from typing import Literal

# Mapping from correction categories to suggested policy categories
CATEGORY_TO_POLICY_CATEGORY = {
    "type_hints": "code_quality",
    "imports": "code_quality",
    "docstrings": "documentation",
    "naming": "code_quality",
    "testing": "code_quality",
    "formatting": "code_quality",
    "general": "workflow",
}

# Mapping from style preferences to policy categories
STYLE_TO_POLICY_CATEGORY = {
    "concise": "documentation",
    "verbose": "documentation",
    "code_first": "documentation",
}

# Confidence to severity mapping
CONFIDENCE_TO_SEVERITY: dict[PatternConfidence, Literal["critical", "required", "recommended", "info"]] = {
    PatternConfidence.HIGH: "required",
    PatternConfidence.MEDIUM: "recommended",
    PatternConfidence.LOW: "info",
}


@dataclass
class SuggesterConfig:
    """Configuration for policy suggestion generation."""

    min_confidence: PatternConfidence = PatternConfidence.LOW
    include_examples: bool = True
    max_suggestions: int = 10


class PolicySuggester:
    """Generates policy suggestions from detected patterns.

    Takes correction patterns, style preferences, and implicit patterns
    and generates structured policy suggestions compatible with charter.yaml.
    """

    def __init__(self, config: SuggesterConfig | None = None) -> None:
        """Initialize the policy suggester.

        Args:
            config: Suggestion configuration, uses defaults if not provided
        """
        self.config = config or SuggesterConfig()
        self._next_id_counter: dict[str, int] = {}

    def generate_suggestions(
        self,
        corrections: list[CorrectionPattern],
        style_prefs: list[StylePreference],
        implicit: list[ImplicitPattern],
    ) -> list[PolicySuggestion]:
        """Generate policy suggestions from all detected patterns.

        Args:
            corrections: Detected correction patterns
            style_prefs: Detected style preferences
            implicit: Detected implicit patterns

        Returns:
            List of policy suggestions, sorted by severity
        """
        suggestions: list[PolicySuggestion] = []

        # Generate from corrections
        for pattern in corrections:
            if self._meets_confidence(pattern.confidence):
                suggestion = self._suggestion_from_correction(pattern)
                if suggestion:
                    suggestions.append(suggestion)

        # Generate from style preferences
        for pref in style_prefs:
            if self._meets_confidence(pref.confidence):
                suggestion = self._suggestion_from_style(pref)
                if suggestion:
                    suggestions.append(suggestion)

        # Generate from implicit patterns
        for impl_pattern in implicit:
            if self._meets_confidence(impl_pattern.confidence):
                suggestion = self._suggestion_from_implicit(impl_pattern)
                if suggestion:
                    suggestions.append(suggestion)

        # Sort by severity (critical > required > recommended > info)
        severity_order = {"critical": 0, "required": 1, "recommended": 2, "info": 3}
        suggestions.sort(key=lambda s: severity_order.get(s.severity, 4))

        return suggestions[: self.config.max_suggestions]

    def _meets_confidence(self, confidence: PatternConfidence) -> bool:
        """Check if confidence meets minimum threshold."""
        order = {PatternConfidence.LOW: 0, PatternConfidence.MEDIUM: 1, PatternConfidence.HIGH: 2}
        return order[confidence] >= order[self.config.min_confidence]

    def _get_next_id(self, category: str) -> str:
        """Generate next policy ID for a category."""
        prefix = category.upper()[:4]
        if prefix not in self._next_id_counter:
            self._next_id_counter[prefix] = 1
        else:
            self._next_id_counter[prefix] += 1
        return f"{prefix}-{self._next_id_counter[prefix]:03d}"

    def _suggestion_from_correction(self, pattern: CorrectionPattern) -> PolicySuggestion | None:
        """Generate a policy suggestion from a correction pattern."""
        category = CATEGORY_TO_POLICY_CATEGORY.get(pattern.category, "workflow")
        policy_id = self._get_next_id(category)
        severity = CONFIDENCE_TO_SEVERITY[pattern.confidence]

        # Build description from pattern
        description = self._build_correction_description(pattern)

        # Build rationale from evidence
        rationale = self._build_rationale(pattern.occurrences, pattern.evidence)

        # Extract example if available
        example = pattern.evidence[0] if self.config.include_examples and pattern.evidence else None

        return PolicySuggestion(
            suggested_id=policy_id,
            severity=severity,
            description=description,
            rationale=rationale,
            example=example,
            source_pattern=pattern,
        )

    def _suggestion_from_style(self, pref: StylePreference) -> PolicySuggestion | None:
        """Generate a policy suggestion from a style preference."""
        category = STYLE_TO_POLICY_CATEGORY.get(pref.preference, "documentation")
        policy_id = self._get_next_id(category)
        severity = CONFIDENCE_TO_SEVERITY[pref.confidence]

        description = self._build_style_description(pref)
        rationale = self._build_rationale(pref.occurrences, pref.evidence)
        example = pref.evidence[0] if self.config.include_examples and pref.evidence else None

        return PolicySuggestion(
            suggested_id=policy_id,
            severity=severity,
            description=description,
            rationale=rationale,
            example=example,
            source_pattern=pref,
        )

    def _suggestion_from_implicit(self, pattern: ImplicitPattern) -> PolicySuggestion | None:
        """Generate a policy suggestion from an implicit pattern."""
        # Skip policy_reference patterns - they reference existing policies
        # and shouldn't generate new policy suggestions
        if pattern.pattern_type == "policy_reference":
            return None

        # Implicit patterns are typically about workflow
        policy_id = self._get_next_id("workflow")
        severity = CONFIDENCE_TO_SEVERITY[pattern.confidence]

        description = pattern.description
        rationale = self._build_rationale(pattern.occurrences, pattern.evidence)
        example = pattern.evidence[0] if self.config.include_examples and pattern.evidence else None

        return PolicySuggestion(
            suggested_id=policy_id,
            severity=severity,
            description=description,
            rationale=rationale,
            example=example,
            source_pattern=pattern,
        )

    def _build_correction_description(self, pattern: CorrectionPattern) -> str:
        """Build a policy description from a correction pattern."""
        category_descriptions = {
            "type_hints": "Use modern Python type hints consistently",
            "imports": "Follow import organization conventions",
            "docstrings": "Write docstrings following project style",
            "naming": "Follow naming conventions for variables and functions",
            "testing": "Write tests following project testing patterns",
            "formatting": "Follow code formatting guidelines",
            "general": "Follow project coding conventions",
        }
        return category_descriptions.get(pattern.category, pattern.description)

    def _build_style_description(self, pref: StylePreference) -> str:
        """Build a policy description from a style preference."""
        style_descriptions = {
            "concise": "Keep responses concise and focused on code",
            "verbose": "Provide detailed explanations with code",
            "code_first": "Show code before explanations",
        }
        return style_descriptions.get(pref.preference, pref.description)

    def _build_rationale(self, occurrences: int, evidence: list[str]) -> str:
        """Build rationale text from occurrence count and evidence."""
        base = f"Detected {occurrences} instance(s) of this pattern in session history."
        if evidence:
            base += f' Example: "{evidence[0][:100]}..."'
        return base

    def to_yaml_snippet(self, suggestion: PolicySuggestion) -> str:
        """Convert a policy suggestion to a YAML snippet for charter.yaml.

        Args:
            suggestion: The policy suggestion to convert

        Returns:
            YAML-formatted string ready to add to charter.yaml
        """
        lines = [
            f"  - id: {suggestion.suggested_id}",
            f"    severity: {suggestion.severity}",
            f"    description: {suggestion.description}",
        ]

        if suggestion.example:
            # Escape quotes in example
            escaped = suggestion.example.replace('"', '\\"')
            lines.append(f'    example: "{escaped[:100]}"')

        return "\n".join(lines)

    def to_yaml_snippets(self, suggestions: list[PolicySuggestion]) -> str:
        """Convert multiple suggestions to YAML snippets.

        Args:
            suggestions: List of policy suggestions

        Returns:
            YAML-formatted string with all suggestions
        """
        if not suggestions:
            return "# No policy suggestions generated"

        snippets = [self.to_yaml_snippet(s) for s in suggestions]
        return "rules:\n" + "\n\n".join(snippets)

