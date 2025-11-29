"""Tests for EgoKit data models."""

import pytest
from pydantic import ValidationError

from egokit.models import (
    ContextFile,
    ContextFileMode,
    EgoCharter,
    EgoConfig,
    PolicyCharter,
    PolicyRule,
    SessionConfig,
    SessionShutdown,
    SessionStartup,
    Severity,
    ToneConfig,
)


class TestPolicyRule:
    """Test PolicyRule validation."""

    def test_valid_rule(self) -> None:
        """Test creating a valid policy rule."""
        rule = PolicyRule(
            id="SEC-001",
            rule="Never commit secrets",
            severity=Severity.CRITICAL,
            detector="secret.regex.v1",
        )
        assert rule.id == "SEC-001"
        assert rule.severity == Severity.CRITICAL

    def test_invalid_rule_id(self) -> None:
        """Test invalid rule ID format."""
        with pytest.raises(ValidationError, match="Rule ID must follow format"):
            PolicyRule(
                id="invalid-id",
                rule="Test rule",
                severity=Severity.WARNING,
                detector="test.v1",
            )

    def test_invalid_detector_name(self) -> None:
        """Test invalid detector name format."""
        with pytest.raises(ValidationError, match="Detector must follow format"):
            PolicyRule(
                id="TEST-001",
                rule="Test rule",
                severity=Severity.WARNING,
                detector="invalid_detector_name",
            )


class TestPolicyCharter:
    """Test PolicyCharter validation."""

    def test_valid_charter(self) -> None:
        """Test creating a valid policy charter."""
        charter = PolicyCharter(
            version="1.0.0",
            scopes={
                "global": {
                    "security": [
                        {
                            "id": "SEC-001",
                            "rule": "Never commit secrets",
                            "severity": "critical",
                            "detector": "secret.regex.v1",
                        },
                    ],
                },
            },
        )
        assert charter.version == "1.0.0"

    def test_invalid_version(self) -> None:
        """Test invalid version format."""
        with pytest.raises(ValidationError, match="Version must follow semantic versioning"):
            PolicyCharter(
                version="invalid-version",
                scopes={},
            )


class TestEgoConfig:
    """Test EgoConfig validation."""

    def test_valid_ego_config(self) -> None:
        """Test creating a valid ego configuration."""
        config = EgoConfig(
            role="Senior Engineer",
            tone=ToneConfig(
                voice="professional",
                verbosity="balanced",
            ),
        )
        assert config.role == "Senior Engineer"
        assert config.tone.voice == "professional"


class TestEgoCharter:
    """Test EgoCharter validation."""

    def test_valid_ego_charter(self) -> None:
        """Test creating a valid ego charter."""
        charter = EgoCharter(
            version="1.0.0",
            ego=EgoConfig(
                role="Engineer",
                tone=ToneConfig(voice="professional", verbosity="balanced"),
            ),
        )
        assert charter.version == "1.0.0"
        assert charter.ego.role == "Engineer"


class TestSessionConfig:
    """Test SessionConfig and related models."""

    def test_session_startup_defaults(self) -> None:
        """Test SessionStartup has sensible defaults."""
        startup = SessionStartup()
        assert startup.read == ["PROGRESS.md"]
        assert startup.run == ["git status", "git log --oneline -5"]

    def test_session_startup_custom(self) -> None:
        """Test SessionStartup with custom values."""
        startup = SessionStartup(
            read=["STATUS.md", "PROGRESS.md"],
            run=["git status"],
        )
        assert startup.read == ["STATUS.md", "PROGRESS.md"]
        assert startup.run == ["git status"]

    def test_session_shutdown_defaults(self) -> None:
        """Test SessionShutdown has sensible defaults."""
        shutdown = SessionShutdown()
        assert shutdown.update == ["PROGRESS.md"]
        assert shutdown.commit is False

    def test_session_shutdown_custom(self) -> None:
        """Test SessionShutdown with custom values."""
        shutdown = SessionShutdown(
            update=["STATUS.md"],
            commit=True,
        )
        assert shutdown.update == ["STATUS.md"]
        assert shutdown.commit is True

    def test_context_file_defaults(self) -> None:
        """Test ContextFile defaults to append mode."""
        context_file = ContextFile(path="PROGRESS.md")
        assert context_file.path == "PROGRESS.md"
        assert context_file.mode == ContextFileMode.APPEND

    def test_context_file_replace_mode(self) -> None:
        """Test ContextFile with replace mode."""
        context_file = ContextFile(path="STATUS.md", mode=ContextFileMode.REPLACE)
        assert context_file.mode == ContextFileMode.REPLACE

    def test_session_config_defaults(self) -> None:
        """Test SessionConfig has sensible defaults."""
        session = SessionConfig()
        assert session.startup.read == ["PROGRESS.md"]
        assert session.shutdown.update == ["PROGRESS.md"]
        assert session.progress_file == "PROGRESS.md"
        assert session.context_files == []

    def test_session_config_full(self) -> None:
        """Test SessionConfig with all options."""
        session = SessionConfig(
            startup=SessionStartup(read=["STATUS.md"]),
            shutdown=SessionShutdown(update=["STATUS.md"], commit=True),
            context_files=[
                ContextFile(path="PROGRESS.md", mode=ContextFileMode.APPEND),
                ContextFile(path="STATUS.md", mode=ContextFileMode.REPLACE),
            ],
            progress_file="STATUS.md",
        )
        assert session.startup.read == ["STATUS.md"]
        assert session.shutdown.commit is True
        assert len(session.context_files) == 2
        assert session.progress_file == "STATUS.md"


class TestPolicyCharterWithSession:
    """Test PolicyCharter with session configuration."""

    def test_charter_without_session(self) -> None:
        """Test charter without session block (default)."""
        charter = PolicyCharter(version="1.0.0", scopes={})
        assert charter.session is None

    def test_charter_with_session(self) -> None:
        """Test charter with session block."""
        charter = PolicyCharter(
            version="1.0.0",
            scopes={},
            session=SessionConfig(
                startup=SessionStartup(read=["PROGRESS.md"]),
                shutdown=SessionShutdown(update=["PROGRESS.md"]),
            ),
        )
        assert charter.session is not None
        assert charter.session.startup.read == ["PROGRESS.md"]
