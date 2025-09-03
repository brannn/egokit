"""EgoKit command-line interface."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

import typer
from rich.console import Console
from rich.table import Table

from .compiler import ArtifactCompiler, ArtifactInjector
from .detectors import DetectorLoader
from .exceptions import EgoKitError
from .models import CompilationContext, Severity
from .registry import PolicyRegistry
from .validator import PolicyValidator

app = typer.Typer(
    name="ego",
    help="EgoKit: Policy Engine & Scaffolding for AI coding agents",
    add_completion=False,
)
console = Console()


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
        console.print(f"[yellow]Warning:[/yellow] Policy registry already exists at {registry_path}")
        if not typer.confirm("Overwrite existing files?"):
            console.print("Initialization cancelled")
            return
    
    try:
        # Create directory structure
        (registry_path / "ego").mkdir(parents=True, exist_ok=True)
        (registry_path / "schemas").mkdir(exist_ok=True)
        
        # Copy schema files
        import shutil
        from pathlib import Path
        
        # Get schema files from our package
        package_schemas = Path(__file__).parent.parent.parent / ".egokit" / "policy-registry" / "schemas"
        if package_schemas.exists():
            shutil.copytree(package_schemas, registry_path / "schemas", dirs_exist_ok=True)
        
        # Create starter charter.yaml
        charter_content = f"""version: 1.0.0
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
        rule: "Technical documentation must avoid superlatives and marketing language"
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
        ego_content = f"""version: 1.0.0
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
        
        (registry_path / "ego" / "global.yaml").write_text(ego_content, encoding="utf-8")
        
        console.print(f"[green]✓[/green] Policy registry initialized at {registry_path}")
        console.print("Created files:")
        console.print("  • charter.yaml (starter policies)")
        console.print("  • ego/global.yaml (AI agent configuration)")
        console.print("  • schemas/ (validation schemas)")
        console.print(f"\nNext steps:")
        console.print(f"  1. Customize policies in {registry_path}/charter.yaml")
        console.print(f"  2. Adjust AI behavior in {registry_path}/ego/global.yaml")
        console.print(f"  3. Run 'ego apply' to generate artifacts")
        
    except OSError as e:
        console.print(f"[red]Error:[/red] Failed to create policy registry: {e}")
        raise typer.Exit(1)


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
    registry_path: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Policy registry path (defaults to ./.egokit/policy-registry)",
    ),
    agent: str = typer.Option(
        "claude",
        "--agent",
        "-a",
        help="Target AI agent: claude, augment, or cursor",
    ),
    scope: List[str] = typer.Option(
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
) -> None:
    """Apply organizational policies to target repository by generating AI agent configuration artifacts.
    
    Supports multiple AI agents:
    - claude: Generates Claude Code artifacts (.claude/, CLAUDE.md)
    - augment: Generates AugmentCode artifacts (.augment/rules/)
    - cursor: Generates Cursor IDE artifacts (.cursorrules, .cursor/rules/)
    """
    try:
        # Validate agent selection
        valid_agents: List[str] = ["claude", "augment", "cursor"]
        if agent not in valid_agents:
            console.print(
                f"[red]Error:[/red] Invalid agent '{agent}'. "
                f"Must be one of: {', '.join(valid_agents)}"
            )
            raise typer.Exit(1)
        
        if registry_path is None:
            registry_path = Path.cwd() / ".egokit" / "policy-registry"
        
        if not registry_path.exists():
            console.print(f"[red]Error:[/red] Policy registry not found at {registry_path}")
            raise typer.Exit(1)
        
        registry = PolicyRegistry(registry_path)
        
        # Load and merge configurations
        charter = registry.load_charter()
        merged_rules = registry.merge_scope_rules(charter, scope)
        ego_config = registry.merge_ego_configs(scope)
        
        # Create compilation context
        context = CompilationContext(
            target_repo=repo,
            policy_charter=charter,
            ego_config=ego_config,
            active_scope=scope[-1] if scope else "global",
        )
        
        # Compile artifacts based on selected agent
        compiler = ArtifactCompiler(context)
        ego_card = compiler.compile_ego_card()
        
        # Agent-specific artifact compilation and handling
        if agent == "claude":
            claude_artifacts = compiler.compile_claude_artifacts()
            
            if dry_run:
                console.print("[bold blue]Dry run - showing generated content for Claude:[/bold blue]")
                console.print(f"\n[bold]CLAUDE.md:[/bold]\n{claude_artifacts.get('CLAUDE.md', '')}")
                console.print(f"\n[bold].claude/settings.json:[/bold]\n{claude_artifacts.get('.claude/settings.json', '')}")
                
                # Show first few custom commands
                command_count = sum(1 for key in claude_artifacts.keys() if key.startswith('.claude/commands/'))
                if command_count > 0:
                    console.print(f"\n[bold]Custom slash commands ({command_count} total):[/bold]")
                    for key in list(claude_artifacts.keys())[:2]:  # Show first 2 commands
                        if key.startswith('.claude/commands/'):
                            console.print(f"\n[bold]{key}:[/bold]\n{claude_artifacts[key][:200]}...")
                
                console.print(f"\n[bold]EGO.md:[/bold]\n{ego_card}")
                return
            
            # Inject Claude artifacts
            injector = ArtifactInjector(repo)
            injector.inject_claude_artifacts(claude_artifacts)
            injector.inject_ego_card(ego_card)
            
            console.print(f"[green]✓[/green] Claude artifacts synced to {repo}")
            console.print(f"  • CLAUDE.md")
            console.print(f"  • .claude/settings.json")
            console.print(f"  • .claude/commands/ ({sum(1 for k in claude_artifacts.keys() if k.startswith('.claude/commands/'))} commands)")
            console.print(f"  • .claude/system-prompt-fragments/egokit-policies.txt")
            console.print(f"  • EGO.md")
            
        elif agent == "augment":
            # Compile AugmentCode artifacts
            augment_artifacts = compiler.compile_augment_artifacts()
            
            if dry_run:
                console.print("[bold blue]Dry run - showing generated content for AugmentCode:[/bold blue]")
                for path, content in augment_artifacts.items():
                    console.print(f"\n[bold]{path}:[/bold]")
                    console.print(content[:500] + "..." if len(content) > 500 else content)
                console.print(f"\n[bold]EGO.md:[/bold]\n{ego_card}")
                return
            
            # Inject AugmentCode artifacts
            injector = ArtifactInjector(repo)
            injector.inject_augment_artifacts(augment_artifacts)
            injector.inject_ego_card(ego_card)
            
            console.print(f"[green]✓[/green] AugmentCode artifacts synced to {repo}")
            for path in augment_artifacts.keys():
                console.print(f"  • {path}")
            console.print(f"  • EGO.md")
            
        elif agent == "cursor":
            # Compile Cursor artifacts
            cursor_artifacts = compiler.compile_cursor_artifacts()
            
            if dry_run:
                console.print("[bold blue]Dry run - showing generated content for Cursor:[/bold blue]")
                console.print(f"\n[bold].cursorrules:[/bold]\n{cursor_artifacts.get('.cursorrules', '')}")
                
                # Show MDC rule files
                rule_count = sum(1 for key in cursor_artifacts.keys() if key.startswith('.cursor/rules/'))
                if rule_count > 0:
                    console.print(f"\n[bold]MDC rule files ({rule_count} total):[/bold]")
                    for key in sorted(cursor_artifacts.keys()):
                        if key.startswith('.cursor/rules/'):
                            console.print(f"\n[bold]{key}:[/bold]")
                            # Show first 300 chars of each MDC file
                            content = cursor_artifacts[key]
                            if len(content) > 300:
                                console.print(f"{content[:300]}...")
                            else:
                                console.print(content)
                
                console.print(f"\n[bold]EGO.md:[/bold]\n{ego_card}")
                return
            
            # Inject Cursor artifacts
            injector = ArtifactInjector(repo)
            injector.inject_cursor_artifacts(cursor_artifacts)
            injector.inject_ego_card(ego_card)
            
            console.print(f"[green]✓[/green] Cursor artifacts synced to {repo}")
            console.print(f"  • .cursorrules")
            rule_count = sum(1 for k in cursor_artifacts.keys() if k.startswith('.cursor/rules/'))
            console.print(f"  • .cursor/rules/ ({rule_count} MDC files)")
            console.print(f"  • EGO.md")
        
    except EgoKitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)




@app.command()
def validate(
    files: List[Path] = typer.Argument(
        None,
        help="Files to validate (defaults to changed files)",
    ),
    all_files: bool = typer.Option(
        False,
        "--all",
        help="Validate all files in repository",
    ),
    changed: bool = typer.Option(
        False,
        "--changed",
        help="Validate only changed files (git diff)",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text or json",
    ),
    registry_path: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Policy registry path",
    ),
    scope: List[str] = typer.Option(
        ["global"],
        "--scope",
        "-s",
        help="Scope precedence (can be repeated)",
    ),
) -> None:
    """Validate files against policy rules."""
    try:
        if registry_path is None:
            registry_path = Path.cwd() / ".egokit" / "policy-registry"
        
        registry = PolicyRegistry(registry_path)
        validator = PolicyValidator(registry)
        
        # Determine files to validate
        if all_files:
            # Find all source files
            target_files = list(Path.cwd().rglob("*.py"))
            target_files.extend(Path.cwd().rglob("*.md"))
            target_files.extend(Path.cwd().rglob("*.ts"))
            target_files.extend(Path.cwd().rglob("*.js"))
        elif changed:
            # Get changed files from git
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=ACM"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                target_files = [Path(f.strip()) for f in result.stdout.splitlines() if f.strip()]
            except subprocess.CalledProcessError:
                console.print("[red]Error:[/red] Failed to get changed files from git")
                raise typer.Exit(1)
        else:
            target_files = files or []
        
        if not target_files:
            console.print("[yellow]No files to validate[/yellow]")
            return
        
        # Run validation
        report = validator.validate_files(target_files, scope)
        
        if format == "json":
            print(report.json(indent=2))
        else:
            _print_validation_report(report)
        
        if not report.passed:
            raise typer.Exit(1)
            
    except EgoKitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def doctor(
    registry_path: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Policy registry path",
    ),
    scope: Optional[List[str]] = typer.Option(
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
            except Exception:
                # If charter loading fails, fall back to file detection
                pass
            
            # Also check for separate scope files in registry root (excluding charter.yaml)
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
        table.add_row("Critical Rules", str(len([r for r in merged_rules if r.severity == Severity.CRITICAL])))
        table.add_row("Warning Rules", str(len([r for r in merged_rules if r.severity == Severity.WARNING])))
        table.add_row("Ego Role", ego_config.role)
        table.add_row("Ego Voice", ego_config.tone.voice)
        table.add_row("Ego Verbosity", ego_config.tone.verbosity)
        
        console.print(table)
        
        # Show rule details
        console.print("\n[bold]Active Rules:[/bold]")
        for rule in sorted(merged_rules, key=lambda r: (r.severity.value, r.id)):
            severity_color = "red" if rule.severity == Severity.CRITICAL else "yellow"
            console.print(f"  [{severity_color}]{rule.severity.value.upper()}[/{severity_color}] {rule.id}: {rule.rule}")
        
    except EgoKitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _print_validation_report(report: ValidationReport) -> None:
    """Print validation report in human-readable format."""
    if report.passed:
        console.print(f"[green]✓[/green] Validation passed ({len(report.files_checked)} files checked)")
    else:
        console.print(f"[red]✗[/red] Validation failed ({len(report.violations)} violations)")
    
    if report.violations:
        console.print("\n[bold]Violations:[/bold]")
        for violation in report.violations:
            severity_color = "red" if violation.level == Severity.CRITICAL else "yellow"
            location = f"{violation.file_path}"
            if violation.line_number:
                location += f":{violation.line_number}"
            
            console.print(f"  [{severity_color}]{violation.level.value.upper()}[/{severity_color}] {violation.rule}: {violation.message}")
            console.print(f"    → {location}")
            
            if violation.suggestion:
                console.print(f"    💡 {violation.suggestion}")


@app.command()
def export_system_prompt(
    registry: Optional[Path] = typer.Option(None, help="Path to policy registry"),
    scope: List[str] = typer.Option([], help="Scope precedence list"),
    output: Optional[Path] = typer.Option(None, help="Output file path"),
) -> None:
    """Export system prompt fragment for Claude Code integration."""
    try:
        # Discover registry if not provided
        registry_path = registry or _discover_registry()
        if not registry_path:
            console.print("[red]✗[/red] No policy registry found")
            raise typer.Exit(1)
        
        # Load and merge policies
        policy_registry = PolicyRegistry(registry_path)
        charter = policy_registry.load_charter()
        merged_rules = policy_registry.merge_scope_rules(charter, scope if scope else ["global"])
        ego_config = policy_registry.merge_ego_configs(scope if scope else ["global"])
        
        # Create compilation context
        context = CompilationContext(
            target_repo=Path.cwd(),
            policy_charter=charter,
            ego_config=ego_config,
            generation_timestamp=datetime.now()
        )
        
        # Generate system prompt fragment
        compiler = ArtifactCompiler(context)
        fragment = compiler._compile_system_prompt_fragment(merged_rules)
        
        if output:
            output.write_text(fragment)
            console.print(f"[green]✓[/green] System prompt fragment exported to {output}")
        else:
            console.print(fragment)
            
    except EgoKitError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@app.command()
def claude_headless(
    prompt: str = typer.Argument(..., help="Prompt for Claude Code"),
    registry: Optional[Path] = typer.Option(None, help="Path to policy registry"),
    scope: List[str] = typer.Option([], help="Scope precedence list"),
    append_policies: bool = typer.Option(True, help="Append policy context to prompt"),
) -> None:
    """Execute Claude Code in headless mode with EgoKit policy context."""
    import subprocess
    import tempfile
    from datetime import datetime
    
    try:
        # Generate system prompt if requested
        system_prompt_file = None
        if append_policies:
            # Discover registry if not provided
            registry_path = registry or _discover_registry()
            if registry_path:
                policy_registry = PolicyRegistry(registry_path)
                charter = policy_registry.load_charter()
                merged_rules = policy_registry.merge_scope_rules(charter, scope if scope else ["global"])
                ego_config = policy_registry.merge_ego_configs(scope if scope else ["global"])
                
                # Create compilation context
                context = CompilationContext(
                    target_repo=Path.cwd(),
                    policy_charter=charter,
                    ego_config=ego_config,
                    generation_timestamp=datetime.now()
                )
                
                compiler = ArtifactCompiler(context)
                fragment = compiler._compile_system_prompt_fragment(merged_rules)
                
                # Write to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(fragment)
                    system_prompt_file = Path(f.name)
        
        # Execute Claude Code headless
        cmd = ["claude", "-p"]
        if system_prompt_file:
            cmd.extend(["--append-system-prompt", str(system_prompt_file)])
        cmd.append(prompt)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            console.print(result.stdout)
            
            if result.stderr:
                console.print(f"[yellow]Warnings: {result.stderr}[/yellow]")
                
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗[/red] Claude Code execution failed: {e}")
            raise typer.Exit(1)
        except FileNotFoundError:
            console.print("[red]✗[/red] claude command not found. Please install Claude Code first.")
            raise typer.Exit(1)
            
    except EgoKitError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)
    finally:
        # Cleanup temporary files
        if system_prompt_file and system_prompt_file.exists():
            system_prompt_file.unlink()


@app.command()
def watch(
    registry: Optional[Path] = typer.Option(None, help="Path to policy registry"),
    interval: int = typer.Option(30, help="Check interval in seconds"),
) -> None:
    """Watch for policy changes and auto-sync Claude Code configuration."""
    import os
    import time
    from datetime import datetime
    
    try:
        registry_path = registry or _discover_registry()
        if not registry_path:
            console.print("[red]✗[/red] No policy registry found")
            raise typer.Exit(1)
        
        claude_projects = []
        
        # Discover Claude Code projects in workspace
        for root, dirs, files in os.walk(Path.cwd()):
            if ".claude" in dirs or "CLAUDE.md" in files:
                claude_projects.append(Path(root))
        
        console.print(f"[blue]👁[/blue] Monitoring {len(claude_projects)} Claude Code projects")
        console.print(f"[blue]📁[/blue] Registry: {registry_path}")
        
        if not claude_projects:
            console.print("[yellow]⚠[/yellow] No Claude Code projects found in current workspace")
        
        last_modified = registry_path.stat().st_mtime if registry_path.exists() else 0
        
        while True:
            try:
                if not registry_path.exists():
                    time.sleep(interval)
                    continue
                    
                current_modified = registry_path.stat().st_mtime
                
                if current_modified > last_modified:
                    console.print("[green]🔄[/green] Policy changes detected, syncing Claude Code projects...")
                    
                    for project_path in claude_projects:
                        try:
                            # Re-sync project using existing sync logic
                            policy_registry = PolicyRegistry(registry_path)
                            charter = policy_registry.load_charter()
                            merged_rules = policy_registry.merge_scope_rules(charter, ["global"])
                            ego_config = policy_registry.merge_ego_configs(["global"])
                            
                            context = CompilationContext(
                                target_repo=project_path,
                                policy_charter=charter,
                                ego_config=ego_config,
                                generation_timestamp=datetime.now()
                            )
                            
                            compiler = ArtifactCompiler(context)
                            artifacts = compiler.compile_claude_artifacts()
                            
                            injector = ArtifactInjector(project_path)
                            injector.inject_claude_artifacts(artifacts)
                            
                            console.print(f"[green]✅[/green] Synced {project_path}")
                        except Exception as e:
                            console.print(f"[red]❌[/red] Failed to sync {project_path}: {e}")
                    
                    last_modified = current_modified
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]👋[/yellow] Stopped watching")
                break
                
    except EgoKitError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


def _discover_registry() -> Optional[Path]:
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