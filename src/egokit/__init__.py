"""EgoKit: Policy Engine & Scaffolding for AI coding agents."""

__version__ = "0.1.0"
__author__ = "EgoKit Contributors"
__description__ = "Policy Engine & Scaffolding for AI coding agents"

from .models import PolicyRule, EgoConfig, Severity
from .registry import PolicyRegistry
from .compiler import ArtifactCompiler

__all__ = [
    "PolicyRule",
    "EgoConfig", 
    "Severity",
    "PolicyRegistry",
    "ArtifactCompiler",
]