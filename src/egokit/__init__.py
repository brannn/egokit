"""EgoKit: Policy Engine & Scaffolding for AI coding agents."""

__version__ = "0.1.0"
__author__ = "EgoKit Contributors"
__description__ = "Policy Engine & Scaffolding for AI coding agents"

from .compiler import ArtifactCompiler
from .models import EgoConfig, PolicyRule, Severity
from .registry import PolicyRegistry

__all__ = [
    "ArtifactCompiler",
    "EgoConfig",
    "PolicyRegistry",
    "PolicyRule",
    "Severity",
]
