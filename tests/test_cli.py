"""Tests for CLI commands and integration."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from egokit.cli import _discover_registry, app


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_registry(self) -> Path:
        """Create a minimal temporary policy registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / ".egokit" / "policy-registry"
            registry_path.mkdir(parents=True)

            # Create minimal charter
            charter_data = {
                "version": "1.0.0",
                "scopes": {
                    "global": {
                        "security": [
                            {
                                "id": "SEC-001",
                                "rule": "Never commit secrets",
                                "severity": "critical",
                                "detector": "secret.regex.v1",
                                "tags": ["security"],
                            },
                        ],
                    },
                },
                "metadata": {"description": "Test"},
            }

            with open(registry_path / "charter.yaml", "w") as f:
                yaml.dump(charter_data, f)

            # Create minimal ego config
            ego_dir = registry_path / "ego"
            ego_dir.mkdir()

            ego_data = {
                "version": "1.0.0",
                "ego": {
                    "role": "Engineer",
                    "tone": {
                        "voice": "professional",
                        "verbosity": "balanced",
                    },
                    "defaults": {"structure": "clean"},
                    "modes": {
                        "implementer": {
                            "verbosity": "balanced",
                            "focus": "implementation",
                        },
                    },
                },
            }

            with open(ego_dir / "global.yaml", "w") as f:
                yaml.dump(ego_data, f)

            # Create schemas directory (required for validation)
            schemas_dir = registry_path / "schemas"
            schemas_dir.mkdir()

            # Create minimal charter schema
            charter_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["version", "scopes"],
                "properties": {
                    "version": {"type": "string"},
                    "scopes": {"type": "object"},
                },
            }

            with open(schemas_dir / "charter.schema.json", "w") as f:
                json.dump(charter_schema, f)

            # Create minimal ego schema
            ego_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "version": {"type": "string"},
                    "ego": {"type": "object"},
                },
            }

            with open(schemas_dir / "ego.schema.json", "w") as f:
                json.dump(ego_schema, f)

            yield registry_path

    @pytest.fixture
    def temp_repo(self) -> Path:
        """Create a temporary target repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()
            yield repo_path

    def test_init_command_creates_registry(self, runner: CliRunner) -> None:
        """Test that init command creates a complete policy registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "init",
                "--path", temp_dir,
                "--org", "Test Organization",
            ])

            assert result.exit_code == 0
            assert "Registry initialized" in result.stdout

            registry_path = Path(temp_dir) / ".egokit" / "policy-registry"
            assert registry_path.exists()
            assert (registry_path / "charter.yaml").exists()
            assert (registry_path / "ego" / "global.yaml").exists()
            assert (registry_path / "schemas").exists()

            # Check charter content
            with open(registry_path / "charter.yaml") as f:
                charter = yaml.safe_load(f)
            assert "Test Organization" in charter["metadata"]["description"]

    def test_apply_command_generates_artifacts(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path,
    ) -> None:
        """Test that apply command generates AGENTS.md and slash commands."""
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
        ])

        assert result.exit_code == 0
        assert "Artifacts synced" in result.stdout or "✓" in result.stdout

        # Check AGENTS.md was created
        assert (temp_repo / "AGENTS.md").exists()
        agents_md = (temp_repo / "AGENTS.md").read_text()
        assert "# AGENTS.md" in agents_md
        assert "Policy Compliance" in agents_md
        assert "binding constraints" in agents_md

        # Check slash commands were created for both tools
        assert (temp_repo / ".claude" / "commands").exists()
        assert (temp_repo / ".augment" / "commands").exists()

        # Check ego-* prefixed commands exist
        claude_cmds = list((temp_repo / ".claude" / "commands").glob("ego-*.md"))
        augment_cmds = list((temp_repo / ".augment" / "commands").glob("ego-*.md"))
        assert len(claude_cmds) >= 8, f"Expected at least 8 Claude commands, got {len(claude_cmds)}"
        assert len(augment_cmds) >= 8, f"Expected at least 8 Augment commands, got {len(augment_cmds)}"

        # Check command content is pure AI prompt (no CLI invocation)
        validate_cmd = (temp_repo / ".claude" / "commands" / "ego-validate.md").read_text()
        assert "python3 -m egokit" not in validate_cmd
        assert "AGENTS.md" in validate_cmd

    def test_apply_command_dry_run(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path,
    ) -> None:
        """Test apply command dry run mode."""
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
            "--dry-run",
        ])

        assert result.exit_code == 0
        assert "Dry run - generated artifacts" in result.stdout
        assert "AGENTS.md:" in result.stdout
        assert ".claude/commands/" in result.stdout
        assert ".augment/commands/" in result.stdout

        # Files should not be created in dry run
        assert not (temp_repo / "AGENTS.md").exists()
        assert not (temp_repo / ".claude").exists()
        assert not (temp_repo / ".augment").exists()

    def test_doctor_command(
        self,
        runner: CliRunner,
        temp_registry: Path,
    ) -> None:
        """Test doctor command provides configuration overview."""
        result = runner.invoke(app, [
            "doctor",
            "--registry", str(temp_registry),
        ])

        assert result.exit_code == 0
        assert "EgoKit Policy Doctor" in result.stdout
        assert "Policy Version" in result.stdout
        assert "1.0.0" in result.stdout
        assert "Active Rules" in result.stdout
        assert "SEC-001" in result.stdout

    def test_discover_registry_finds_local(self) -> None:
        """Test registry discovery in directory hierarchy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            project_dir = temp_path / "projects" / "my-project"
            project_dir.mkdir(parents=True)

            # Create registry at higher level
            registry_dir = temp_path / ".egokit" / "policy-registry"
            registry_dir.mkdir(parents=True)

            # Change to project directory and test discovery
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(project_dir)
                discovered = _discover_registry()
                # Use resolve() to handle symlinks
                assert discovered.resolve() == registry_dir.resolve()
            finally:
                os.chdir(original_cwd)

    def test_discover_registry_not_found(self) -> None:
        """Test registry discovery when no registry exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()

            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(project_dir)
                discovered = _discover_registry()
                assert discovered is None
            finally:
                os.chdir(original_cwd)

    def test_apply_command_with_scope_precedence(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path,
    ) -> None:
        """Test apply command with custom scope precedence."""
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
            "--scope", "global",
            "--scope", "teams/backend",  # This won't exist but should handle gracefully
        ])

        # Should still work with global scope even if team scope doesn't exist
        assert result.exit_code == 0 or "not found" in result.stdout.lower()

    def test_cli_error_handling(self, runner: CliRunner) -> None:
        """Test CLI error handling for missing registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "apply",
                "--repo", temp_dir,
                "--registry", "/nonexistent/registry",
            ])

            assert result.exit_code == 1
            assert "Policy registry not found" in result.stdout

    def test_version_command(self, runner: CliRunner) -> None:
        """Test version command shows version information."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "EgoKit version" in result.stdout
        # Should show a version number (format: X.Y.Z) or unknown
        import re
        version_pattern = r"\d+\.\d+\.\d+"
        assert re.search(version_pattern, result.stdout) or "unknown" in result.stdout

    def test_apply_force_flag_skips_confirmation(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path,
    ) -> None:
        """Test that --force flag skips confirmation for existing AGENTS.md without markers."""
        # Create existing AGENTS.md without markers
        agents_md = temp_repo / "AGENTS.md"
        agents_md.write_text("# My Custom AGENTS.md\n\nCustom content here.\n")

        # Run apply with --force flag
        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
            "--force",
        ])

        assert result.exit_code == 0
        assert "appended" in result.stdout.lower() or "✓" in result.stdout

        # Verify content was appended
        content = agents_md.read_text()
        assert "# My Custom AGENTS.md" in content  # Original preserved
        assert "<!-- BEGIN-EGOKIT-POLICIES -->" in content  # EgoKit added

    def test_apply_existing_agents_md_with_markers_updates_section(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path,
    ) -> None:
        """Test that existing AGENTS.md with markers gets section updated."""
        # Create existing AGENTS.md with markers
        agents_md = temp_repo / "AGENTS.md"
        agents_md.write_text("""# My Custom AGENTS.md

## Custom Section
My custom content.

<!-- BEGIN-EGOKIT-POLICIES -->
<!-- Old EgoKit content -->
## Old Policy Section
Old content here.
<!-- END-EGOKIT-POLICIES -->

## Another Custom Section
More custom content.
""")

        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
        ])

        assert result.exit_code == 0
        assert "updated" in result.stdout.lower() or "✓" in result.stdout

        # Verify custom content preserved, EgoKit content replaced
        content = agents_md.read_text()
        assert "# My Custom AGENTS.md" in content
        assert "## Custom Section" in content
        assert "My custom content." in content
        assert "## Another Custom Section" in content
        assert "More custom content." in content
        # Old EgoKit content should be gone
        assert "Old Policy Section" not in content
        assert "Old content here." not in content
        # New EgoKit content should be present
        assert "## Policy Compliance" in content

    def test_apply_new_agents_md_creates_template(
        self,
        runner: CliRunner,
        temp_registry: Path,
        temp_repo: Path,
    ) -> None:
        """Test that new AGENTS.md gets full template."""
        # Ensure no AGENTS.md exists
        agents_md = temp_repo / "AGENTS.md"
        assert not agents_md.exists()

        result = runner.invoke(app, [
            "apply",
            "--repo", str(temp_repo),
            "--registry", str(temp_registry),
        ])

        assert result.exit_code == 0
        assert "created" in result.stdout.lower() or "✓" in result.stdout

        # Verify template structure
        content = agents_md.read_text()
        assert "# AGENTS.md" in content
        assert "## Project Overview" in content
        assert "## Setup Commands" in content
        assert "<!-- BEGIN-EGOKIT-POLICIES -->" in content
        assert "<!-- END-EGOKIT-POLICIES -->" in content
