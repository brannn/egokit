"""Core data models for EgoKit policy engine."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    detector: str = Field(..., description="Detector module name")
    auto_fix: bool = Field(default=False, description="Whether auto-fix is available")
    example_violation: Optional[str] = Field(
        default=None, description="Example of rule violation"
    )
    example_fix: Optional[str] = Field(
        default=None, description="Example of correct implementation"
    )
    tags: List[str] = Field(default_factory=list, description="Rule categorization tags")
    
    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate rule ID follows expected format."""
        if not re.match(r"^[A-Z]{2,6}-\d{3}$", v):
            raise ValueError("Rule ID must follow format: PREFIX-NNN (e.g., SEC-001)")
        return v
    
    @field_validator("detector")
    @classmethod
    def validate_detector_name(cls, v: str) -> str:
        """Validate detector name follows versioning convention."""
        if not re.match(r"^[a-z_.]+\.v\d+$", v):
            raise ValueError("Detector must follow format: name.v1 (e.g., secret.regex.v1)")
        return v


class ToneConfig(BaseModel):
    """Configuration for AI agent tone and communication style."""
    
    voice: str = Field(..., description="Voice characteristics")
    verbosity: str = Field(..., description="Verbosity level")
    formatting: List[str] = Field(
        default_factory=list, description="Formatting preferences"
    )


class ModeConfig(BaseModel):
    """Configuration for specific operating modes."""
    
    verbosity: str = Field(..., description="Mode-specific verbosity override")
    focus: Optional[str] = Field(default=None, description="Mode-specific focus area")


class EgoConfig(BaseModel):
    """AI agent persona and behavioral configuration."""
    
    role: str = Field(..., description="Primary role identity")
    tone: ToneConfig = Field(..., description="Communication style configuration")
    defaults: Dict[str, str] = Field(
        default_factory=dict, description="Default behavioral patterns"
    )
    reviewer_checklist: List[str] = Field(
        default_factory=list, description="Review criteria checklist"
    )
    ask_when_unsure: List[str] = Field(
        default_factory=list, description="Scenarios requiring user clarification"
    )
    modes: Dict[str, ModeConfig] = Field(
        default_factory=dict, description="Named operating modes"
    )


class ScopeRules(BaseModel):
    """Rules defined at a specific scope level."""
    
    security: List[PolicyRule] = Field(default_factory=list)
    code_quality: List[PolicyRule] = Field(default_factory=list) 
    docs: List[PolicyRule] = Field(default_factory=list)
    licensing: List[PolicyRule] = Field(default_factory=list)
    additional_rules: List[PolicyRule] = Field(default_factory=list)
    
    def all_rules(self) -> List[PolicyRule]:
        """Get all rules from this scope."""
        return (
            self.security + 
            self.code_quality + 
            self.docs + 
            self.licensing + 
            self.additional_rules
        )


class PolicyCharter(BaseModel):
    """Complete policy charter with versioning and hierarchical scopes."""
    
    version: str = Field(..., description="Semantic version of policy charter")
    scopes: Dict[str, Any] = Field(
        default_factory=dict, description="Hierarchical policy scopes"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional charter metadata"
    )
    
    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate version follows semantic versioning."""
        semver_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-]+)?(?:\+[a-zA-Z0-9\-]+)?$"
        if not re.match(semver_pattern, v):
            raise ValueError("Version must follow semantic versioning (e.g., 1.2.0)")
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
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v


class DetectionResult(BaseModel):
    """Result from a detector run."""
    
    rule: str = Field(..., description="Rule ID that was violated")
    level: Severity = Field(..., description="Severity level of violation")
    message: str = Field(..., description="Human-readable violation message")
    file_path: Path = Field(..., description="File where violation occurred")
    line_number: Optional[int] = Field(default=None, description="Line number if applicable")
    column: Optional[int] = Field(default=None, description="Column number if applicable")
    span: Optional[tuple[int, int]] = Field(
        default=None, description="Character span (start, end) if applicable"
    )
    suggestion: Optional[str] = Field(
        default=None, description="Suggested fix if available"
    )


class ValidationReport(BaseModel):
    """Complete validation report from policy enforcement."""
    
    passed: bool = Field(..., description="Whether validation passed overall")
    violations: List[DetectionResult] = Field(
        default_factory=list, description="All detected violations"
    )
    files_checked: List[Path] = Field(
        default_factory=list, description="Files that were validated"
    )
    detectors_run: List[str] = Field(
        default_factory=list, description="Detectors that were executed"
    )
    execution_time: float = Field(..., description="Validation execution time in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When validation was performed"
    )
    
    @property
    def critical_violations(self) -> List[DetectionResult]:
        """Get only critical violations."""
        return [v for v in self.violations if v.level == Severity.CRITICAL]
    
    @property
    def warning_violations(self) -> List[DetectionResult]:
        """Get only warning violations."""
        return [v for v in self.violations if v.level == Severity.WARNING]


class ArtifactConfig(BaseModel):
    """Configuration for generated artifacts."""
    
    target_path: Path = Field(..., description="Where to write the artifact")
    template_name: str = Field(..., description="Template to use for generation")
    include_metadata: bool = Field(default=True, description="Include generation metadata")
    preserve_manual_sections: bool = Field(
        default=True, description="Preserve manually added sections"
    )


class CompilationContext(BaseModel):
    """Context information for artifact compilation."""
    
    target_repo: Path = Field(..., description="Target repository path")
    policy_charter: PolicyCharter = Field(..., description="Merged policy charter")
    ego_config: EgoConfig = Field(..., description="Merged ego configuration")
    active_scope: str = Field(default="global", description="Currently active scope")
    session_overrides: Dict[str, Any] = Field(
        default_factory=dict, description="Session-specific overrides"
    )
    generation_timestamp: datetime = Field(
        default_factory=datetime.now, description="When compilation occurred"
    )