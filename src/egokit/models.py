"""Core data models for EgoKit policy engine."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Policy rule severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class PolicyRule(BaseModel):
    """A single policy rule with enforcement metadata."""

    id: str = Field(..., description="Unique identifier for the rule")
    rule: str = Field(..., description="Human-readable rule description")
    severity: Severity = Field(..., description="Enforcement severity level")
    detector: str | None = Field(
        default=None,
        description="Optional detector module name (for future use)",
    )
    auto_fix: bool = Field(default=False, description="Whether auto-fix is available")
    example_violation: str | None = Field(
        default=None,
        description="Example of rule violation",
    )
    example_fix: str | None = Field(
        default=None,
        description="Example of correct implementation",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Rule categorization tags",
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate rule ID follows expected format."""
        if not re.match(r"^[A-Z]{2,6}-\d{3}$", v):
            msg = "Rule ID must follow format: PREFIX-NNN (e.g., SEC-001)"
            raise ValueError(msg)
        return v

    @field_validator("detector")
    @classmethod
    def validate_detector_name(cls, v: str) -> str:
        """Validate detector name follows versioning convention."""
        if not re.match(r"^[a-z_.]+\.v\d+$", v):
            msg = "Detector must follow format: name.v1 (e.g., secret.regex.v1)"
            raise ValueError(msg)
        return v


class ToneConfig(BaseModel):
    """Configuration for AI agent tone and communication style."""

    voice: str = Field(..., description="Voice characteristics")
    verbosity: str = Field(..., description="Verbosity level")
    formatting: list[str] = Field(
        default_factory=list,
        description="Formatting preferences",
    )


class ModeConfig(BaseModel):
    """Configuration for specific operating modes."""

    verbosity: str = Field(..., description="Mode-specific verbosity override")
    focus: str | None = Field(default=None, description="Mode-specific focus area")


class EgoConfig(BaseModel):
    """AI agent persona and behavioral configuration."""

    role: str = Field(..., description="Primary role identity")
    tone: ToneConfig = Field(..., description="Communication style configuration")
    defaults: dict[str, str] = Field(
        default_factory=dict,
        description="Default behavioral patterns",
    )
    reviewer_checklist: list[str] = Field(
        default_factory=list,
        description="Review criteria checklist",
    )
    ask_when_unsure: list[str] = Field(
        default_factory=list,
        description="Scenarios requiring user clarification",
    )
    modes: dict[str, ModeConfig] = Field(
        default_factory=dict,
        description="Named operating modes",
    )


class ScopeRules(BaseModel):
    """Rules defined at a specific scope level."""

    security: list[PolicyRule] = Field(default_factory=list)
    code_quality: list[PolicyRule] = Field(default_factory=list)
    docs: list[PolicyRule] = Field(default_factory=list)
    licensing: list[PolicyRule] = Field(default_factory=list)
    additional_rules: list[PolicyRule] = Field(default_factory=list)

    def all_rules(self) -> list[PolicyRule]:
        """Get all rules from this scope."""
        return (
            self.security
            + self.code_quality
            + self.docs
            + self.licensing
            + self.additional_rules
        )


class PolicyCharter(BaseModel):
    """Complete policy charter with versioning and hierarchical scopes."""

    version: str = Field(..., description="Semantic version of policy charter")
    scopes: dict[str, Any] = Field(
        default_factory=dict,
        description="Hierarchical policy scopes",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional charter metadata",
    )
    session: SessionConfig | None = Field(
        default=None,
        description="Session continuity protocol configuration (opt-in)",
    )

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate version follows semantic versioning."""
        semver_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-]+)?(?:\+[a-zA-Z0-9\-]+)?$"
        if not re.match(semver_pattern, v):
            msg = "Version must follow semantic versioning (e.g., 1.2.0)"
            raise ValueError(msg)
        return v


class EgoCharter(BaseModel):
    """Complete ego configuration with versioning."""

    version: str = Field(..., description="Semantic version of ego charter")
    ego: EgoConfig = Field(..., description="Ego configuration")

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate version follows semantic versioning."""
        semver_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-]+)?(?:\+[a-zA-Z0-9\-]+)?$"
        if not re.match(semver_pattern, v):
            msg = "Version must follow semantic versioning (e.g., 1.0.0)"
            raise ValueError(msg)
        return v


class ContextFileMode(str, Enum):
    """Mode for updating context files during session handoff."""

    APPEND = "append"   # Add new entries (like PROGRESS.md session log)
    REPLACE = "replace"  # Update in place (like STATUS.md current state)


class ContextFile(BaseModel):
    """Configuration for a session context file."""

    path: str = Field(..., description="Path to the context file relative to repo root")
    mode: ContextFileMode = Field(
        default=ContextFileMode.APPEND,
        description="How the file should be updated",
    )


class SessionStartup(BaseModel):
    """Configuration for session startup protocol."""

    read: list[str] = Field(
        default_factory=lambda: ["PROGRESS.md"],
        description="Files to read for context at session start",
    )
    run: list[str] = Field(
        default_factory=lambda: ["git status", "git log --oneline -5"],
        description="Commands to run for orientation",
    )


class SessionShutdown(BaseModel):
    """Configuration for session shutdown protocol."""

    update: list[str] = Field(
        default_factory=lambda: ["PROGRESS.md"],
        description="Files to update before ending session",
    )
    commit: bool = Field(
        default=False,
        description="Whether to require committing changes before session end",
    )


class SessionConfig(BaseModel):
    """Session continuity protocol configuration.

    This defines how AI agents should handle session boundaries to maintain
    context across context windows. EgoKit compiles these into instructions;
    the agent executes them.
    """

    startup: SessionStartup = Field(
        default_factory=SessionStartup,
        description="What to do when starting a session",
    )
    shutdown: SessionShutdown = Field(
        default_factory=SessionShutdown,
        description="What to do when ending a session",
    )
    context_files: list[ContextFile] = Field(
        default_factory=list,
        description="Explicit context file configurations with modes",
    )
    progress_file: str = Field(
        default="PROGRESS.md",
        description="Primary progress file path",
    )


class ArtifactConfig(BaseModel):
    """Configuration for generated artifacts."""

    target_path: Path = Field(..., description="Where to write the artifact")
    template_name: str = Field(..., description="Template to use for generation")
    include_metadata: bool = Field(
        default=True,
        description="Include generation metadata",
    )
    preserve_manual_sections: bool = Field(
        default=True,
        description="Preserve manually added sections",
    )


class CompilationContext(BaseModel):
    """Context information for artifact compilation."""

    target_repo: Path = Field(..., description="Target repository path")
    policy_charter: PolicyCharter = Field(..., description="Merged policy charter")
    ego_config: EgoConfig = Field(..., description="Merged ego configuration")
    active_scope: str = Field(default="global", description="Currently active scope")
    session_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Session-specific overrides",
    )
    generation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When compilation occurred",
    )
