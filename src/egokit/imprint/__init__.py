"""Imprint: Pattern detection from explicit corrections in AI session logs.

This module provides functionality to analyze AI coding session history
and surface patterns in user corrections, suggesting policy refinements.

Design Principles:
1. Transparent over magical - every suggestion traceable to evidence
2. User-triggered, never ambient - no background monitoring
3. Suggestions, never impositions - user decides what to adopt
4. Honest about limitations - explicit about what we can/cannot detect
5. Zero runtime cost - batch operation on historical data only
"""

from .detector import DetectorConfig, PatternDetector
from .models import (
    CorrectionPattern,
    ImplicitPattern,
    ImprintReport,
    Message,
    MessageRole,
    PatternConfidence,
    PolicySuggestion,
    Session,
    StylePreference,
)
from .parsers import AugmentParser, ClaudeCodeParser, LogParser
from .suggester import PolicySuggester, SuggesterConfig

__all__ = [
    "AugmentParser",
    "ClaudeCodeParser",
    "CorrectionPattern",
    "DetectorConfig",
    "ImplicitPattern",
    "ImprintReport",
    "LogParser",
    "Message",
    "MessageRole",
    "PatternConfidence",
    "PatternDetector",
    "PolicySuggester",
    "PolicySuggestion",
    "Session",
    "StylePreference",
    "SuggesterConfig",
]

