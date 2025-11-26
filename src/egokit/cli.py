"""EgoKit command-line interface."""

from __future__ import annotations

import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

try:
    from importlib.metadata import version as get_version
except ImportError:
    from importlib_metadata import version as get_version

from .compiler import ArtifactCompiler, find_egokit_section
from .exceptions import EgoKitError
from .models import CompilationContext, Severity
from .registry import PolicyRegistry

app = typer.Typer(
    name="ego",
    help="EgoKit: Policy Engine & Scaffolding for AI coding agents",
    add_completion=False,
)
console = Console()


def _get_version_string() -> str:
    """Get version string from package metadata or pyproject.toml."""
    try:
        return get_version("egokit")
    except (ImportError, ModuleNotFoundError):
        pass

    # Try to read version from pyproject.toml for development installs
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return f"{match.group(1)} (development)"

    return "unknown"


def version_callback(value: bool) -> None:
    """Callback for --version flag."""
    if value:
        console.print(f"EgoKit version {_get_version_string()}")
        raise typer.Exit


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """EgoKit: Policy Engine & Scaffolding for AI coding agents."""


@app.command()
def init(
    path: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Directory to initialize policy registry",
    ),
    org_name: str = typer.Option(
        "My Organization",
        "--org",
        help="Organization name for templates",
    ),
) -> None:
    """Initialize a new policy registry with starter templates."""
    registry_path = path / ".egokit" / "policy-registry"

    if registry_path.exists():
        console.print(
            f"[yellow]Warning:[/yellow] Registry exists at {registry_path}",
        )
        if not typer.confirm("Overwrite existing files?"):
            console.print("Initialization cancelled")
            return

    try:
        # Create directory structure
        (registry_path / "ego").mkdir(parents=True, exist_ok=True)
        (registry_path / "schemas").mkdir(exist_ok=True)

        # Create JSON schemas for validation
        charter_schema = """\
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EgoKit Policy Charter",
  "type": "object",
  "required": ["version", "scopes"],
  "properties": {
    "version": {
      "type": "string",
      "description": "Semantic version of policy charter"
    },
    "scopes": {
      "type": "object",
      "description": "Hierarchical policy scopes"
    },
    "metadata": {
      "type": "object"
    }
  }
}
"""
        ego_schema = """\
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EgoKit Ego Configuration",
  "type": "object",
  "required": ["version", "ego"],
  "properties": {
    "version": {
      "type": "string",
      "description": "Semantic version of ego configuration"
    },
    "ego": {
      "type": "object",
      "description": "AI agent behavior configuration"
    }
  }
}
"""
        (registry_path / "schemas" / "charter.schema.json").write_text(
            charter_schema, encoding="utf-8",
        )
        (registry_path / "schemas" / "ego.schema.json").write_text(
            ego_schema, encoding="utf-8",
        )

        # Create starter charter.yaml
        charter_content = f"""\
version: 1.0.0
scopes:
  global:
    security:
      - id: SEC-001
        rule: "Never commit credentials or secrets"
        severity: critical
        detector: secret.regex.v1
        auto_fix: false
        example_violation: "api_key = 'sk-123456789abcdef'"
        example_fix: "api_key = os.environ['API_KEY']"
        tags: ["security", "credentials"]
    code_quality:
      - id: QUAL-001
        rule: "Use type hints for all function parameters and return values"
        severity: warning
        detector: python.ast.typehints.v1
        auto_fix: true
        example_violation: "def process_data(data):"
        example_fix: "def process_data(data: Dict[str, Any]) -> List[str]:"
        tags: ["python", "typing"]
    docs:
      - id: DOCS-001
        rule: "Avoid superlatives and marketing language"
        severity: critical
        detector: docs.style.superlatives.v1
        auto_fix: false
        example_violation: "This amazing feature is world-class"
        example_fix: "This feature provides X functionality"
        tags: ["documentation", "style"]
metadata:
  description: "{org_name} policy charter"
  maintainer: "{org_name} Engineering Team"
  last_updated: "2025-08-31"
"""

        (registry_path / "charter.yaml").write_text(charter_content, encoding="utf-8")

        # Create starter ego configuration
        ego_content = """\
version: 1.0.0
ego:
  role: "Senior Software Engineer"
  tone:
    voice: "professional, precise, helpful"
    verbosity: "balanced"
    formatting:
      - "code-with-comments"
      - "bullet-lists-for-steps"
      - "examples-when-helpful"
  defaults:
    structure: "overview → implementation → validation → documentation"
    code_style: "Follow established project conventions"
    documentation: "clear, concise, actionable"
    testing: "unit tests with meaningful assertions"
  reviewer_checklist:
    - "Code follows established patterns and conventions"
    - "Type hints are comprehensive and accurate"
    - "Error handling is appropriate and informative"
    - "Documentation is clear and up-to-date"
    - "Tests cover critical functionality"
    - "Security best practices are followed"
  ask_when_unsure:
    - "Breaking changes to public APIs"
    - "Security-sensitive modifications"
    - "Performance-critical optimizations"
    - "Database schema changes"
  modes:
    implementer:
      verbosity: "balanced"
      focus: "clean implementation with good practices"
    reviewer:
      verbosity: "detailed"
      focus: "thorough analysis and constructive feedback"
    security:
      verbosity: "detailed"
      focus: "security implications and threat modeling"
"""

        ego_path = registry_path / "ego" / "global.yaml"
        ego_path.write_text(ego_content, encoding="utf-8")

        console.print(f"[green]✓[/green] Registry initialized at {registry_path}")
        console.print("Created files:")
        console.print("  • charter.yaml (starter policies)")
        console.print("  • ego/global.yaml (AI agent configuration)")
        console.print("  • schemas/ (validation schemas)")
        console.print("\nNext steps:")
        console.print(f"  1. Customize policies in {registry_path}/charter.yaml")
        console.print(f"  2. Adjust AI behavior in {registry_path}/ego/global.yaml")
        console.print("  3. Run 'ego apply' to generate artifacts")

    except OSError as e:
        console.print(f"[red]Error:[/red] Failed to create policy registry: {e}")
        raise typer.Exit(1) from e


@app.command()
def apply(
    repo: Path = typer.Option(
        Path.cwd(),
        "--repo",
        "-r",
        help="Target repository path",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    registry_path: Path | None = typer.Option(
        None,
        "--registry",
        help="Policy registry path (defaults to ./.egokit/policy-registry)",
    ),
    scope: list[str] = typer.Option(
        ["global"],
        "--scope",
        "-s",
        help="Scope precedence (can be repeated)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be generated without writing files",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation when appending to existing AGENTS.md without markers",
    ),
) -> None:
    """Apply organizational policies to target repository.

    Generates AGENTS.md (the universal policy artifact) and slash commands
    for both Claude Code (.claude/commands/) and Auggie CLI (.augment/commands/).

    Uses hybrid ownership model for AGENTS.md:
    - New files: Creates template with human-editable sections + EgoKit policies
    - Existing files with markers: Updates only the EgoKit-managed section
    - Existing files without markers: Appends EgoKit section (prompts for confirmation)
    """
    try:
        if registry_path is None:
            registry_path = Path.cwd() / ".egokit" / "policy-registry"

        if not registry_path.exists():
            console.print(
                f"[red]Error:[/red] Policy registry not found at {registry_path}",
            )
            raise typer.Exit(1)

        registry = PolicyRegistry(registry_path)

        # Load and merge configurations
        charter = registry.load_charter()
        ego_config = registry.merge_ego_configs(scope)

        # Create compilation context
        context = CompilationContext(
            target_repo=repo,
            policy_charter=charter,
            ego_config=ego_config,
            active_scope=scope[-1] if scope else "global",
        )

        # Check if AGENTS.md already exists
        agents_md_path = repo / "AGENTS.md"
        existing_content: str | None = None
        needs_confirmation = False

        if agents_md_path.exists():
            existing_content = agents_md_path.read_text(encoding="utf-8")
            has_markers = find_egokit_section(existing_content) is not None

            if not has_markers and not force:
                # Existing file without markers - need confirmation
                needs_confirmation = True
                console.print(
                    "[yellow]Warning:[/yellow] AGENTS.md has no EgoKit markers.",
                )
                console.print(
                    "The EgoKit policy section will be appended to the file.",
                )
                console.print("Your existing content will be preserved.\n")

                if not dry_run:
                    confirm = typer.confirm("Do you want to continue?")
                    if not confirm:
                        console.print("[yellow]Aborted.[/yellow]")
                        raise typer.Exit(0)

        # Compile all artifacts using AGENTS.md-first approach
        compiler = ArtifactCompiler(context)
        artifacts = compiler.compile_all_artifacts(existing_agents_md=existing_content)

        if dry_run:
            console.print("[bold blue]Dry run - generated artifacts:[/bold blue]")

            # Show AGENTS.md status
            if existing_content is None:
                console.print("\n[bold]AGENTS.md:[/bold] (new file with template)")
            elif needs_confirmation:
                console.print("\n[bold]AGENTS.md:[/bold] (appending EgoKit section)")
            else:
                console.print("\n[bold]AGENTS.md:[/bold] (updating EgoKit section)")

            console.print(artifacts.get("AGENTS.md", "")[:1000] + "...")

            # Count commands
            claude_cmds = [k for k in artifacts if k.startswith(".claude/commands/")]
            augment_cmds = [k for k in artifacts if k.startswith(".augment/commands/")]
            console.print("\n[bold]Slash commands:[/bold]")
            console.print(f"  • .claude/commands/ ({len(claude_cmds)} commands)")
            console.print(f"  • .augment/commands/ ({len(augment_cmds)} commands)")

            # Show one sample command
            if claude_cmds:
                sample = claude_cmds[0]
                console.print(f"\n[bold]Sample: {sample}[/bold]")
                console.print(artifacts[sample][:300] + "...")
            return

        # Write all artifacts
        for path, content in artifacts.items():
            full_path = repo / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Count artifacts by type
        claude_cmds = [k for k in artifacts if k.startswith(".claude/commands/")]
        augment_cmds = [k for k in artifacts if k.startswith(".augment/commands/")]

        console.print(f"[green]✓[/green] Artifacts synced to {repo}")

        # Show AGENTS.md status
        if existing_content is None:
            console.print("  • AGENTS.md (created with template)")
        elif needs_confirmation:
            console.print("  • AGENTS.md (appended EgoKit section)")
        else:
            console.print("  • AGENTS.md (updated EgoKit section)")

        console.print(f"  • .claude/commands/ ({len(claude_cmds)} commands)")
        console.print(f"  • .augment/commands/ ({len(augment_cmds)} commands)")

    except EgoKitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def doctor(
    registry_path: Path | None = typer.Option(
        None,
        "--registry",
        help="Policy registry path",
    ),
    scope: list[str] | None = typer.Option(
        None,
        "--scope",
        "-s",
        help="Scope precedence to analyze (auto-detects if not specified)",
    ),
) -> None:
    """Show effective policy configuration and scope resolution."""
    try:
        if registry_path is None:
            registry_path = Path.cwd() / ".egokit" / "policy-registry"

        registry = PolicyRegistry(registry_path)

        # Auto-detect scopes if none provided
        if scope is None:
            scope = []

            # First, try to detect scopes from charter.yaml
            try:
                charter = registry.load_charter()
                # Get all scope names defined in the charter
                charter_scopes = list(charter.scopes.keys())
                scope.extend(charter_scopes)
            except EgoKitError:
                # If charter loading fails, fall back to file detection
                pass

            # Also check for separate scope files in registry root
            for scope_file in registry_path.glob("*.yaml"):
                if scope_file.name != "charter.yaml":
                    scope_name = scope_file.stem
                    if scope_name not in scope:  # Avoid duplicates
                        scope.append(scope_name)

            # Always include global scope if it exists as separate file
            ego_global_path = registry_path / "ego" / "global.yaml"
            if ego_global_path.exists() and "global" not in scope:
                scope.append("global")

            # Default to global only if no scopes found
            if not scope:
                scope = ["global"]
        else:
            charter = registry.load_charter()
        ego_config = registry.merge_ego_configs(scope)
        merged_rules = registry.merge_scope_rules(charter, scope)

        # Create summary table
        table = Table(title="EgoKit Policy Doctor")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Policy Version", charter.version)
        table.add_row("Active Scopes", " → ".join(scope))
        table.add_row("Total Rules", str(len(merged_rules)))
        critical = [r for r in merged_rules if r.severity == Severity.CRITICAL]
        warning = [r for r in merged_rules if r.severity == Severity.WARNING]
        table.add_row("Critical Rules", str(len(critical)))
        table.add_row("Warning Rules", str(len(warning)))
        table.add_row("Ego Role", ego_config.role)
        table.add_row("Ego Voice", ego_config.tone.voice)
        table.add_row("Ego Verbosity", ego_config.tone.verbosity)

        console.print(table)

        # Show rule details
        console.print("\n[bold]Active Rules:[/bold]")
        for rule in sorted(merged_rules, key=lambda r: (r.severity.value, r.id)):
            sev_color = "red" if rule.severity == Severity.CRITICAL else "yellow"
            sev_label = rule.severity.value.upper()
            console.print(
                f"  [{sev_color}]{sev_label}[/{sev_color}] {rule.id}: {rule.rule}",
            )

    except EgoKitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def watch(
    registry: Path | None = typer.Option(None, help="Path to policy registry"),
    interval: int = typer.Option(30, help="Check interval in seconds"),
) -> None:
    """Watch for policy changes and auto-sync AGENTS.md and slash commands."""
    try:
        registry_path = registry or _discover_registry()
        if not registry_path:
            console.print("[red]✗[/red] No policy registry found")
            raise typer.Exit(1)

        egokit_projects: list[Path] = []

        # Discover projects with AGENTS.md or AI tool directories
        for root, dirs, files in os.walk(Path.cwd()):
            if "AGENTS.md" in files or ".claude" in dirs or ".augment" in dirs:
                egokit_projects.append(Path(root))

        console.print(f"[blue]Monitoring[/blue] {len(egokit_projects)} projects")
        console.print(f"[blue]Registry:[/blue] {registry_path}")

        if not egokit_projects:
            console.print(
                "[yellow]Warning:[/yellow] No projects with AGENTS.md found",
            )

        last_mtime = registry_path.stat().st_mtime if registry_path.exists() else 0

        while True:
            try:
                if not registry_path.exists():
                    time.sleep(interval)
                    continue

                current_mtime = registry_path.stat().st_mtime

                if current_mtime > last_mtime:
                    console.print(
                        "[green]Policy changes detected,[/green] syncing projects...",
                    )
                    _sync_projects(egokit_projects, registry_path)
                    last_mtime = current_mtime

                time.sleep(interval)

            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped watching[/yellow]")
                break

    except EgoKitError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1) from e


def _sync_projects(projects: list[Path], registry_path: Path) -> None:
    """Sync all projects with the policy registry."""
    for project_path in projects:
        try:
            policy_registry = PolicyRegistry(registry_path)
            charter = policy_registry.load_charter()
            ego_config = policy_registry.merge_ego_configs(["global"])

            context = CompilationContext(
                target_repo=project_path,
                policy_charter=charter,
                ego_config=ego_config,
                generation_timestamp=datetime.now(tz=UTC),
            )

            compiler = ArtifactCompiler(context)
            artifacts = compiler.compile_all_artifacts()

            # Write all artifacts
            for path, content in artifacts.items():
                full_path = project_path / path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            console.print(f"  [green]Synced[/green] {project_path}")
        except EgoKitError as e:
            console.print(f"  [red]Failed[/red] {project_path}: {e}")


@app.command()
def version() -> None:
    """Show EgoKit version information."""
    console.print(f"EgoKit version {_get_version_string()}")


def _discover_registry() -> Path | None:
    """Discover policy registry in current working directory hierarchy.

    Returns:
        Path to discovered registry or None if not found
    """
    current = Path.cwd()

    # Look up directory tree for .egokit/policy-registry
    while current != current.parent:
        registry_path = current / ".egokit" / "policy-registry"
        if registry_path.exists() and registry_path.is_dir():
            return registry_path
        current = current.parent

    return None


def main() -> None:
    """Entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
