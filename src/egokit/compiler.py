"""Artifact compiler for generating agent-specific configuration files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .models import CompilationContext, EgoConfig, PolicyRule, Severity


class ArtifactCompiler:
    """Compiles policy and ego configurations into agent-specific artifacts."""
    
    def __init__(self, context: CompilationContext) -> None:
        """Initialize compiler with compilation context.
        
        Args:
            context: Compilation context containing merged policies and ego config
        """
        self.context = context
    
    def compile_claude_artifacts(self) -> Dict[str, str]:
        """Generate comprehensive Claude Code configuration artifacts.
        
        Returns:
            Dictionary of artifact paths to their content
        """
        artifacts = {}
        rules = self._extract_rules_from_charter()
        
        # Enhanced CLAUDE.md with richer context
        artifacts["CLAUDE.md"] = self._compile_claude_context_file(rules)
        
        # Settings configuration
        artifacts[".claude/settings.json"] = self._compile_claude_settings(rules)
        
        # Custom slash commands
        command_artifacts = self._compile_claude_commands(rules)
        for command_name, command_content in command_artifacts.items():
            artifacts[f".claude/commands/{command_name}.md"] = command_content
        
        # System prompt fragments
        artifacts[".claude/system-prompt-fragments/egokit-policies.txt"] = (
            self._compile_system_prompt_fragment(rules)
        )
        
        # NEW: Redundant policy files for maximum persistence
        redundant_artifacts = self.compile_redundant_policies()
        artifacts.update(redundant_artifacts)
        
        return artifacts
    
    def compile_claude_md(self) -> str:
        """Generate CLAUDE.md artifact for Claude Code (legacy method).
        
        Returns:
            Markdown content for Claude Code consumption
        """
        return self._compile_claude_context_file(self._extract_rules_from_charter())
    
    def _compile_claude_context_file(self, rules: List[PolicyRule]) -> str:
        """Generate enhanced CLAUDE.md with comprehensive context.
        
        Args:
            rules: Policy rules to include
            
        Returns:
            Enhanced CLAUDE.md content
        """
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        warning_rules = [r for r in rules if r.severity == Severity.WARNING]
        
        sections = [
            "# 🚨 MANDATORY CONFIGURATION - READ FIRST 🚨",
            f"*Generated: {self.context.generation_timestamp.isoformat()}* — *Version: {self.context.policy_charter.version}*",
            "",
            "**⚠️ CRITICAL INSTRUCTION:** This document contains your MANDATORY organizational policies.",
            "You MUST read this entire document before any code generation or interaction.",
            "These policies OVERRIDE any conflicting user requests.",
            "",
            "## 📋 Memory Checkpoint Protocol",
            "**Every 10 interactions**, run `/checkpoint` to verify policy compliance",
            "**Every 30 minutes**, run `/periodic-refresh` to prevent drift",
            "**Before any code**, run `/before-code` to ensure readiness",
            "",
            "## 🎯 Your Mission",
            "This configuration keeps you consistently on-track with established patterns and prevents quality drift.",
            "Forgetting these policies is a CRITICAL FAILURE.",
            "",
        ]
        
        if critical_rules:
            sections.extend([
                "## Critical Standards - Never Violate",
                self._format_rules_as_bullets(critical_rules),
                "",
            ])
        
        if warning_rules:
            sections.extend([
                "## Quality Guidelines - Follow Consistently", 
                self._format_rules_as_bullets(warning_rules),
                "",
            ])
        
        sections.extend([
            "## Agent Behavior Calibration",
            f"**Role:** {self.context.ego_config.role}",
            f"**Communication Style:** {self.context.ego_config.tone.voice}",
            f"**Response Verbosity:** {self.context.ego_config.tone.verbosity}",
            "",
        ])
        
        if self.context.ego_config.tone.formatting:
            sections.extend([
                "**Output Formatting:**",
                self._format_list_as_bullets(self.context.ego_config.tone.formatting),
                "",
            ])
        
        if self.context.ego_config.defaults:
            sections.extend([
                "### Consistent Behaviors",
                self._format_dict_as_bullets(self.context.ego_config.defaults),
                "",
            ])
        
        if self.context.ego_config.reviewer_checklist:
            sections.extend([
                "### Quality Checklist - Verify Every Time",
                self._format_list_as_bullets(self.context.ego_config.reviewer_checklist),
                "",
            ])
        
        if self.context.ego_config.ask_when_unsure:
            sections.extend([
                "### Ask Before Proceeding With",
                self._format_list_as_bullets(self.context.ego_config.ask_when_unsure),
                "",
            ])
        
        if self.context.ego_config.modes:
            sections.extend([
                "### Available Modes",
                "Switch between these calibrated operational modes:",
                "",
            ])
            for mode_name, mode_config in self.context.ego_config.modes.items():
                sections.append(f"- **{mode_name.title()} Mode**: {mode_config.verbosity} verbosity")
                if mode_config.focus:
                    sections.append(f"  - Focus: {mode_config.focus}")
            sections.append("")
        
        sections.extend([
            "---",
            "*Remember: When organizational standards conflict with individual preferences, always follow the established patterns above.*",
        ])
        
        return "\n".join(sections)
    
    def _compile_claude_settings(self, rules: List[PolicyRule]) -> str:
        """Generate .claude/settings.json with policy-derived configurations.
        
        Args:
            rules: Policy rules to extract settings from
            
        Returns:
            JSON settings configuration for Claude Code
        """
        # Extract security policies
        security_rules = [r for r in rules if "security" in (r.tags or [])]
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        
        settings = {
            "permissions": {
                "allow": self._extract_allowed_operations(rules),
                "deny": self._extract_denied_operations(security_rules),
                "ask": self._extract_confirmation_required(critical_rules)
            },
            "behavior": {
                "security_first": bool(security_rules),
                "require_confirmation_for_critical": bool(critical_rules),
                "documentation_standards": self._extract_doc_standards(rules)
            },
            "automation": {
                "auto_validate_on_save": self.context.ego_config.defaults.get("auto_validate", False),
                "suggest_fixes": any(r.auto_fix for r in rules),
                "remember_preferences": True
            }
        }
        
        return json.dumps(settings, indent=2)
    
    def _extract_allowed_operations(self, rules: List[PolicyRule]) -> List[str]:
        """Extract allowed operations from policy rules."""
        allowed = ["read", "write", "git"]
        
        # Always allow basic development operations unless explicitly restricted
        return allowed
    
    def _extract_denied_operations(self, security_rules: List[PolicyRule]) -> List[str]:
        """Extract denied operations from security rules."""
        denied = []
        
        for rule in security_rules:
            # Look for specific security restrictions
            if "credentials" in rule.rule.lower() or "secrets" in rule.rule.lower():
                denied.extend(["network:external", "env:write"])
            if "https" in rule.rule.lower():
                denied.append("network:http")
        
        return list(set(denied))  # Remove duplicates
    
    def _extract_confirmation_required(self, critical_rules: List[PolicyRule]) -> List[str]:
        """Extract operations requiring confirmation from critical rules."""
        ask_for = []
        
        for rule in critical_rules:
            if "database" in rule.rule.lower():
                ask_for.append("database_operations")
            if "deploy" in rule.rule.lower():
                ask_for.append("deployment_changes")
            if "security" in rule.rule.lower():
                ask_for.append("security_modifications")
        
        # Always ask for potentially destructive operations
        ask_for.extend(["git:push:main", "file:delete:batch"])
        
        return list(set(ask_for))
    
    def _extract_doc_standards(self, rules: List[PolicyRule]) -> Dict[str, bool]:
        """Extract documentation standards from rules."""
        doc_standards = {
            "require_examples": False,
            "no_superlatives": False,
            "no_emojis": False
        }
        
        for rule in rules:
            if "documentation" in (rule.tags or []) or "docs" in (rule.tags or []):
                if "example" in rule.rule.lower():
                    doc_standards["require_examples"] = True
                if "superlative" in rule.rule.lower():
                    doc_standards["no_superlatives"] = True
                if "emoji" in rule.rule.lower():
                    doc_standards["no_emojis"] = True
        
        return doc_standards
    
    def _compile_claude_commands(self, rules: List[PolicyRule]) -> Dict[str, str]:
        """Generate custom slash commands for policy operations.
        
        Args:
            rules: Policy rules to create commands for
            
        Returns:
            Dictionary of command names to their markdown content
        """
        commands = {}
        
        # Policy validation command
        commands["validate"] = self._generate_validate_command(rules)
        
        # Security review mode command
        commands["security-review"] = self._generate_security_mode_command(rules)
        
        # Compliance check command
        commands["compliance-check"] = self._generate_compliance_command(rules)
        
        # Policy refresh command
        commands["refresh-policies"] = self._generate_refresh_command()
        
        # NEW: Memory checkpoint command
        commands["checkpoint"] = self._generate_checkpoint_command(rules)
        
        # NEW: Periodic refresh reminder
        commands["periodic-refresh"] = self._generate_periodic_refresh_command()
        
        # NEW: Policy recall test
        commands["recall-policies"] = self._generate_recall_command(rules)
        
        # NEW: Before code preparation
        commands["before-code"] = self._generate_before_code_command()
        
        # Mode switching commands
        if self.context.ego_config.modes:
            for mode in self.context.ego_config.modes:
                commands[f"mode-{mode}"] = self._generate_mode_command(
                    mode, self.context.ego_config.modes[mode]
                )
        
        return commands
    
    def _generate_validate_command(self, rules: List[PolicyRule]) -> str:
        """Generate policy validation slash command."""
        sections = [
            "---",
            "description: Validate code against organizational policy standards",
            "argument-hint: [--all] [file/path]",
            "allowed-tools: Bash(ego validate:*), Read(*.py), Read(*.md)",
            "---",
            "",
            "# Validate Code Against Organizational Standards",
            "",
            "This command runs EgoKit policy validation to ensure code stays on-track with established patterns.",
            "",
            "## Usage Examples",
            "- `/validate` - Validate changed files only",
            "- `/validate --all` - Validate entire codebase", 
            "- `/validate src/models.py` - Validate specific file",
            "- `/validate src/` - Validate directory",
            "",
            "## Context Check",
            "Current status: !`git status -s`",
            "",
            "## Active Policy Rules", 
            f"Enforcing {len(rules)} organizational standards from @.egokit/policy-registry/charter.yaml:",
            "",
        ]
        
        # Show active critical rules
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        if critical_rules:
            sections.extend([
                "### Critical Standards (Will Block Commits)",
                "",
            ])
            for rule in critical_rules[:5]:  # Show first 5
                sections.append(f"- **{rule.id}**: {rule.rule}")
            
            if len(critical_rules) > 5:
                sections.append(f"- ... and {len(critical_rules) - 5} more critical standards")
            sections.append("")
        
        sections.extend([
            "## Implementation",
            "```bash",
            "# Run EgoKit validation",
            "python3 -m egokit.cli validate --changed --format json",
            "",
            "# Parse results and provide summary",
            "if [ $? -eq 0 ]; then",
            '    echo "✅ All policy checks passed"',
            "else",
            '    echo "❌ Policy violations detected. Run \'python3 -m egokit.cli validate --changed\' for details."',
            "fi",
            "```",
            "",
            "## Context",
            "This command integrates with the organizational policy framework to prevent quality drift and ensure consistent agent behavior across all development activities.",
        ])
        
        return "\n".join(sections)
    
    def _generate_security_mode_command(self, rules: List[PolicyRule]) -> str:
        """Generate security review mode command."""
        security_rules = [r for r in rules if "security" in (r.tags or [])]
        
        sections = [
            "---",
            "description: Security review with threat modeling and vulnerability assessment", 
            "argument-hint: [priority] [path]",
            "allowed-tools: Bash(git diff:*), Bash(grep:*), Read(*.py), Read(*.js), Read(*.go)",
            "---",
            "",
            "# Switch to Security Review Mode",
            "",
            "Activates heightened security analysis with threat modeling focus.",
            "",
            "## Usage Examples",
            "- `/security-review` - Review current changes with standard priority",
            "- `/security-review high src/auth/` - High priority review of auth module", 
            "- `/security-review critical .` - Critical security audit of entire project",
            "",
            "## Context Analysis",
            "Recent changes: !`git diff --stat --name-only`",
            "",
            "## Security Standards",
            f"Applying {len(security_rules)} security policies from @.egokit/policy-registry/charter.yaml:",
            "",
            "## Behavior Changes",
            "- Enhanced security vulnerability detection",
            "- Threat modeling considerations for all code changes",
            "- OWASP Top 10 validation",
            "- Cryptographic implementation review",
            "- Authentication and authorization analysis",
            "",
        ]
        
        if security_rules:
            sections.extend([
                "## Active Security Policies",
                "",
            ])
            for rule in security_rules[:3]:  # Show first 3
                sections.append(f"- **{rule.id}**: {rule.rule}")
            sections.append("")
        
        sections.extend([
            "## Implementation",
            "```bash",
            'export EGOKIT_MODE="security"',
            'echo "🔒 Security review mode activated. All code will be analyzed for security implications."',
            "```",
            "",
            "## Context",
            "This mode calibrates agent behavior for security-focused analysis, ensuring consistent application of security standards and threat awareness.",
        ])
        
        return "\n".join(sections)
    
    def _generate_compliance_command(self, rules: List[PolicyRule]) -> str:
        """Generate compliance check command."""
        sections = [
            "# Regulatory Compliance Validation",
            "",
            "Validates code against regulatory and compliance requirements.",
            "",
            "## Usage",
            "`/compliance-check [--standard sox|pci|hipaa|gdpr]`",
            "",
            "## Compliance Areas",
            "- Data handling and privacy (GDPR, CCPA)",
            "- Financial regulations (SOX, PCI-DSS)",
            "- Healthcare standards (HIPAA)",
            "- Security frameworks (ISO 27001, NIST)",
            "",
            "## Implementation",
            "```bash",
            "# Run compliance-specific validation",
            "python3 -m egokit.cli validate --all",
            "",
            "# Generate compliance report",
            'echo "📊 Compliance validation complete"',
            'echo "📋 Areas validated: All active standards"',
            "```",
            "",
            "## Context",
            "Ensures AI-generated code meets regulatory requirements without manual review of every interaction.",
        ]
        
        return "\n".join(sections)
    
    def _generate_refresh_command(self) -> str:
        """Generate policy refresh command."""
        sections = [
            "---",
            "description: Reload latest organizational policies to prevent drift",
            "argument-hint: [scope]",
            "allowed-tools: Bash(ego apply:*), Read(@.egokit/policy-registry/*)",
            "---",
            "",
            "# Refresh Policy Understanding", 
            "",
            "Reloads and applies the latest organizational policies from the policy registry.",
            "",
            "## Usage Examples",
            "- `/refresh-policies` - Refresh with default global scope",
            "- `/refresh-policies team` - Refresh with team-specific scope",
            "",
            "## Current Policy State",
            "Reading from @.egokit/policy-registry/charter.yaml",
            "",
            "## Actions Performed",
            "1. Reload policy charter from registry",
            "2. Merge hierarchical scope configurations",
            "3. Update agent behavior calibration settings",
            "4. Refresh detector configurations",
            "5. Apply new validation rules",
            "",
            "## Implementation",
            "```bash",
            "# Regenerate Claude Code artifacts",
            "ego apply",
            "",
            "# Reload configuration",
            'echo "🔄 Policy configuration refreshed from registry"',
            'echo "📋 Active policies:"',
            "ego doctor",
            "",
            "# Remind about new behavioral guidelines", 
            'echo "✨ Updated behavior calibration applied"',
            "```",
            "",
            "## Integration Notes",
            "Use this command after policy registry updates or when switching between projects with different requirements.",
        ]
        
        return "\n".join(sections)
    
    def _generate_mode_command(self, mode_name: str, mode_config: Any) -> str:
        """Generate mode-specific command.
        
        Args:
            mode_name: Name of the mode
            mode_config: Mode configuration object
            
        Returns:
            Command content for the mode
        """
        sections = [
            f"# Switch to {mode_name.title()} Mode",
            "",
            f"Calibrates agent behavior for {mode_name} operations.",
            "",
            "## Usage", 
            f"`/mode-{mode_name}`",
            "",
            "## Behavior Changes",
            f"- **Verbosity**: {mode_config.verbosity}",
        ]
        
        if hasattr(mode_config, 'focus') and mode_config.focus:
            sections.append(f"- **Focus**: {mode_config.focus}")
        
        sections.extend([
            "",
            "## Implementation",
            "```bash",
            f'export EGOKIT_MODE="{mode_name}"',
            f'echo "🎯 {mode_name.title()} mode activated."',
            "```",
        ])
        
        return "\n".join(sections)
    
    def _generate_checkpoint_command(self, rules: List[PolicyRule]) -> str:
        """Generate memory checkpoint command."""
        critical_count = len([r for r in rules if r.severity == Severity.CRITICAL])
        
        sections = [
            "# 🔍 Policy Memory Checkpoint",
            "",
            "Validates that you remember and are applying organizational policies.",
            "",
            "## Usage",
            "`/checkpoint`",
            "",
            "## Validation Steps",
            "",
            "### 1. Policy Recall Test",
            "List the 3 most important policies you remember:",
            "- [ ] First critical policy",
            "- [ ] Second critical policy", 
            "- [ ] Third critical policy",
            "",
            "### 2. Current Compliance Check",
            "Review your last 3 responses/code generations:",
            "- [ ] Did they follow security policies?",
            "- [ ] Did they match the required coding style?",
            "- [ ] Did they maintain consistency with project patterns?",
            "",
            "### 3. Constitution Awareness",
            f"You should remember {critical_count} CRITICAL rules from Article I",
            "State which article of the constitution applies to your current task.",
            "",
            "### 4. Remediation if Needed",
            "If you cannot recall policies clearly:",
            "1. Re-read CLAUDE.md immediately",
            "2. Review .claude/system-prompt-fragments/egokit-policies.txt",
            "3. Run `/refresh-policies` to reload configuration",
            "",
            "## Success Criteria",
            "✅ Can recall all critical policies",
            "✅ Recent work complies with standards",
            "✅ Clear which constitutional articles apply",
        ]
        
        return "\n".join(sections)
    
    def _generate_periodic_refresh_command(self) -> str:
        """Generate periodic refresh reminder command."""
        sections = [
            "# ⏰ Periodic Policy Refresh",
            "",
            "Scheduled reminder to refresh policy awareness and prevent drift.",
            "",
            "## Usage",
            "`/periodic-refresh`",
            "",
            "## When to Run",
            "- Every 10 interactions with the user",
            "- Every 30 minutes of active development",
            "- After completing any major feature",
            "- When switching between different parts of codebase",
            "",
            "## Refresh Protocol",
            "",
            "### Step 1: Re-read Core Documents",
            "```",
            "Reading CLAUDE.md for latest policies...",
            "Loading system prompt fragments...",
            "Checking for policy updates...",
            "```",
            "",
            "### Step 2: Validate Recent Compliance",
            "Review the last 5 files you've edited:",
            "- Do they follow the established patterns?",
            "- Are security policies properly applied?",
            "- Is the code style consistent?",
            "",
            "### Step 3: Reset Behavioral Calibration",
            "Confirm your current calibration:",
            "- Role: Check ego configuration",
            "- Voice: Verify communication style",
            "- Mode: Confirm operational mode",
            "",
            "### Step 4: Acknowledge Refresh",
            "State: \"✅ Policies refreshed. Operating with latest organizational standards.\"",
            "",
            "## Integration",
            "Set a mental reminder to run this periodically during long sessions.",
        ]
        
        return "\n".join(sections)
    
    def _generate_recall_command(self, rules: List[PolicyRule]) -> str:
        """Generate policy recall test command."""
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL][:3]
        
        sections = [
            "# 🧠 Policy Recall Test",
            "",
            "Tests your memory of critical organizational policies.",
            "",
            "## Usage",
            "`/recall-policies`",
            "",
            "## Memory Test",
            "",
            "Without looking at any files, answer these questions:",
            "",
            "### 1. Critical Policies",
            "What are the top 3 critical policies you must never violate?",
            "```",
            "1. _______________",
            "2. _______________", 
            "3. _______________",
            "```",
            "",
            "### 2. Your Current Role",
            "What role are you acting as for this organization?",
            "```",
            "Role: _______________",
            "```",
            "",
            "### 3. Security Requirements",
            "Name 2 security requirements you must always follow:",
            "```",
            "1. _______________",
            "2. _______________",
            "```",
            "",
            "### 4. Validation Checklist",
            "What should you check before generating code?",
            "```",
            "□ _______________",
            "□ _______________",
            "□ _______________",
            "```",
            "",
            "## Answer Key",
            "After answering, check against:",
        ]
        
        if critical_rules:
            sections.append("- Critical policies include:")
            for rule in critical_rules:
                sections.append(f"  - {rule.id}: {rule.rule[:50]}...")
        
        sections.extend([
            "",
            "If you scored less than 80%, immediately run `/refresh-policies`",
        ])
        
        return "\n".join(sections)
    
    def _generate_before_code_command(self) -> str:
        """Generate before-code preparation command."""
        sections = [
            "---",
            "description: Pre-flight checklist before code generation",
            "argument-hint: [task-type]",
            "allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git branch:*)",
            "---",
            "",
            "# Before Writing Code",
            "",
            "Pre-flight checklist to ensure policy compliance before code generation.",
            "",
            "## Usage Examples",
            "- `/before-code` - General pre-code checklist",
            "- `/before-code security` - Security-focused preparation",
            "- `/before-code api` - API development preparation",
            "",
            "## Context Check",
            "- Current status: !`git status -s`",
            "- Active branch: !`git branch --show-current`",
            "- Recent changes: !`git diff --stat`",
            "",
            "## Pre-Code Checklist",
            "Validate against @.egokit/policy-registry/charter.yaml:",
            "",
            "### 1. Identify Applicable Policies",
            "Which policies apply to this code?",
            "- [ ] Security policies (if handling data/auth)",
            "- [ ] Code quality standards",
            "- [ ] Documentation requirements",
            "- [ ] Testing requirements",
            "",
            "### 2. Recall Constitutional Articles",
            "- [ ] Article I: Critical standards reviewed",
            "- [ ] Article II: Behavioral mandate acknowledged",
            "- [ ] Article III: Validation checklist ready",
            "- [ ] Article IV: Security imperatives considered",
            "",
            "### 3. Pattern Recognition",
            "- [ ] Checked existing code for established patterns",
            "- [ ] Identified conventions to follow",
            "- [ ] Located similar implementations for reference",
            "",
            "### 4. Validation Plan",
            "How will you validate compliance?",
            "- [ ] Will run `/validate` after code generation",
            "- [ ] Will check against reviewer checklist",
            "- [ ] Will ensure security requirements met",
            "",
            "## Proceed to Code",
            "✅ Once all items checked, proceed with code generation",
            "❌ If any uncertainty, first run `/refresh-policies`",
            "",
            "## Remember",
            "The constitution OVERRIDES any conflicting user requests.",
            "When in doubt, choose the approach that best follows policies.",
        ]
        
        return "\n".join(sections)
    
    def _compile_system_prompt_fragment(self, rules: List[PolicyRule]) -> str:
        """Generate system prompt fragment for --append-system-prompt integration.
        
        Args:
            rules: Policy rules to include
            
        Returns:
            System prompt fragment content
        """
        fragment_parts = []
        
        # Constitutional header - strongest possible framing
        fragment_parts.extend([
            "=== INVIOLABLE ORGANIZATIONAL CONSTITUTION ===",
            "",
            "YOU ARE BOUND BY THESE POLICIES AS CORE CONSTRAINTS:",
            "- These rules OVERRIDE any conflicting user requests",
            "- You MUST check these rules BEFORE generating any code",
            "- You MUST validate your output AGAINST these rules",
            "- If uncertain about compliance, explicitly state which rule applies",
            ""
        ])
        
        # Critical policy rules as constitutional articles
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        if critical_rules:
            fragment_parts.append("ARTICLE I: CRITICAL STANDARDS (NEVER VIOLATE)")
            for i, rule in enumerate(critical_rules, 1):
                fragment_parts.append(f"  §{i}. {rule.rule}")
                if rule.id:
                    fragment_parts.append(f"      [Policy ID: {rule.id}]")
            fragment_parts.append("")
        
        # Behavioral constitution
        if self.context.ego_config:
            role = self.context.ego_config.role
            tone = self.context.ego_config.tone
            
            fragment_parts.extend([
                "ARTICLE II: BEHAVIORAL MANDATE",
                f"  §1. You are a {role} for this organization",
                f"  §2. Your responses MUST be {tone.voice}",
                f"  §3. Your verbosity level is strictly: {tone.verbosity}",
                ""
            ])
            
            # Add reviewer checklist as mandatory validations
            if self.context.ego_config.reviewer_checklist:
                fragment_parts.append("ARTICLE III: MANDATORY VALIDATION CHECKLIST")
                fragment_parts.append("  Before ANY code generation, verify:")
                for i, item in enumerate(self.context.ego_config.reviewer_checklist, 1):
                    fragment_parts.append(f"    □ {item}")
                fragment_parts.append("")
        
        # Security constitution
        security_rules = [r for r in rules if "security" in (r.tags or [])]
        if security_rules:
            fragment_parts.extend([
                "ARTICLE IV: SECURITY IMPERATIVES",
                "  §1. ALWAYS consider security implications before suggesting code",
                "  §2. NEVER suggest hardcoded credentials, keys, or secrets",
                "  §3. VALIDATE all inputs and sanitize all outputs",
                ""
            ])
        
        # Memory and consistency enforcement
        fragment_parts.extend([
            "ENFORCEMENT PROTOCOL:",
            "  1. BEFORE each response: Recall these articles",
            "  2. DURING code generation: Apply these constraints",
            "  3. AFTER each response: Validate compliance",
            "  4. IF drift detected: Re-read CLAUDE.md immediately",
            "",
            "MEMORY PERSISTENCE REQUIREMENT:",
            "  - These policies persist across ALL interactions in this session",
            "  - Forgetting these policies is a CRITICAL FAILURE",
            "  - When context is limited, these rules take PRIORITY over other information",
            "",
            "=== END ORGANIZATIONAL CONSTITUTION ==="
        ])
        
        return "\n".join(fragment_parts)
    
    def compile_augment_artifacts(self) -> Dict[str, str]:
        """Generate AugmentCode configuration artifacts.
        
        Returns:
            Dictionary mapping file paths to their content
        """
        artifacts: Dict[str, str] = {}
        rules = self._extract_rules_from_charter()
        
        # Compile policy rules
        policy_content = self._compile_augment_policy_rules(rules)
        artifacts[".augment/rules/policy-rules.md"] = policy_content
        
        # Compile ego configuration
        ego_content = self._compile_augment_ego_rules(self.context.ego_config)
        artifacts[".augment/rules/coding-style.md"] = ego_content
        
        # Generate guidelines (legacy support)
        guidelines = self._compile_augment_guidelines_content()
        artifacts[".augment/rules/guidelines.md"] = guidelines
        
        return artifacts
    
    def compile_augment_guidelines(self) -> str:
        """Legacy method for backward compatibility.
        
        Returns:
            Markdown content for AugmentCode guidelines
        """
        return self._compile_augment_guidelines_content()
    
    def _compile_augment_guidelines_content(self) -> str:
        """Generate guidelines content for AugmentCode.
        
        Returns:
            Markdown content for AugmentCode guidelines
        """
        rules = self._extract_rules_from_charter()
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        warning_rules = [r for r in rules if r.severity == Severity.WARNING]
        
        sections = [
            "# Engineering Guidelines",
            f"_Generated: {self.context.generation_timestamp.isoformat()}_",
            "",
        ]
        
        if critical_rules:
            sections.extend([
                "## CRITICAL — MUST FOLLOW",
                "",
            ])
            
            for rule in critical_rules:
                sections.append(f"- **{rule.id}**: {rule.rule}")
                if rule.example_fix:
                    sections.extend([
                        "  ```python",
                        "  # ✅ Good",
                        f"  {rule.example_fix}",
                        "  ```",
                    ])
            
            sections.append("")
        
        if warning_rules:
            sections.extend([
                "## Warnings",
                "",
            ])
            
            for rule in warning_rules:
                sections.append(f"- **{rule.id}**: {rule.rule}")
                if rule.example_fix:
                    sections.extend([
                        "  ```python", 
                        "  # ✅ Recommended",
                        f"  {rule.example_fix}",
                        "  ```",
                    ])
            
            sections.append("")
        
        sections.extend([
            "---",
            "## Ego — Voice & Operating Mode",
            f"- **Role:** {self.context.ego_config.role}",
            f"- **Tone:** {self.context.ego_config.tone.voice} ({self.context.ego_config.tone.verbosity})",
            "",
        ])
        
        if self.context.ego_config.defaults:
            sections.extend([
                "### Defaults",
            ])
            for key, value in self.context.ego_config.defaults.items():
                sections.append(f"- {key}: {value}")
        
        return "\n".join(sections)
    
    def compile_ego_card(self) -> str:
        """Generate EGO.md quick reference card.
        
        Returns:
            Compact ego configuration summary
        """
        ego = self.context.ego_config
        
        sections = [
            "# Ego Configuration",
            f"*Generated: {self.context.generation_timestamp.isoformat()}*",
            "",
            f"**Role:** {ego.role}",
            f"**Voice:** {ego.tone.voice}",
            f"**Verbosity:** {ego.tone.verbosity}",
            "",
        ]
        
        if ego.tone.formatting:
            sections.extend([
                "**Formatting:**",
                self._format_list_as_bullets(ego.tone.formatting),
                "",
            ])
        
        if ego.modes:
            sections.extend(["**Available Modes:**"])
            for mode_name, mode_config in ego.modes.items():
                sections.append(f"- `{mode_name}`: {mode_config.verbosity}")
                if mode_config.focus:
                    sections.append(f"  - Focus: {mode_config.focus}")
            sections.append("")
        
        if ego.ask_when_unsure:
            sections.extend([
                "**Ask when unsure about:**",
                self._format_list_as_bullets(ego.ask_when_unsure),
            ])
        
        return "\n".join(sections)
    
    def _compile_augment_policy_rules(self, rules: List[PolicyRule]) -> str:
        """Compile policy rules for AugmentCode format.
        
        Args:
            rules: Policy rules to compile
            
        Returns:
            AugmentCode-compatible rule content
        """
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        warning_rules = [r for r in rules if r.severity == Severity.WARNING]
        
        sections = [
            "---",
            "description: Security and quality policies that must be followed",
            "type: always",
            "---",
            "",
            "# Policy Rules",
            "",
        ]
        
        if critical_rules:
            sections.extend([
                "## Critical Requirements",
                "",
                "These rules must be followed and will block code if violated:",
                "",
            ])
            
            for rule in critical_rules:
                sections.append(f"- {rule.rule}")
                if rule.example_fix:
                    sections.extend([
                        "",
                        "```python",
                        f"# Correct approach:",
                        rule.example_fix,
                        "```",
                        "",
                    ])
        
        if warning_rules:
            sections.extend([
                "## Best Practices",
                "",
                "Follow these guidelines for code quality:",
                "",
            ])
            
            for rule in warning_rules:
                sections.append(f"- {rule.rule}")
        
        return "\n".join(sections)
    
    def _compile_augment_ego_rules(self, ego_config: EgoConfig) -> str:
        """Compile ego configuration for AugmentCode format.
        
        Args:
            ego_config: Ego configuration
            
        Returns:
            AugmentCode-compatible ego rule content
        """
        sections = [
            "---",
            "description: Coding style and communication preferences",
            "type: always", 
            "---",
            "",
            "# Coding Style and Approach",
            "",
            f"Act as a {ego_config.role.lower()} with a {ego_config.tone.voice} communication style.",
            "",
        ]
        
        if ego_config.defaults:
            sections.extend([
                "## Development Approach",
                "",
            ])
            for key, value in ego_config.defaults.items():
                sections.append(f"- {key.replace('_', ' ').title()}: {value}")
            
            sections.append("")
        
        if ego_config.tone.formatting:
            sections.extend([
                "## Code Formatting Preferences",
                "",
            ])
            for pref in ego_config.tone.formatting:
                sections.append(f"- {pref.replace('-', ' ').replace('_', ' ').title()}")
            
            sections.append("")
        
        if ego_config.reviewer_checklist:
            sections.extend([
                "## Quality Checklist",
                "",
                "Ensure code meets these criteria:",
                "",
            ])
            for item in ego_config.reviewer_checklist:
                sections.append(f"- {item}")
        
        return "\n".join(sections)
    
    def _extract_rules_from_charter(self) -> List[PolicyRule]:
        """Extract all rules from the policy charter."""
        from egokit.models import ScopeRules
        
        rules = []
        
        for scope_data in self.context.policy_charter.scopes.values():
            if isinstance(scope_data, ScopeRules):
                # Handle ScopeRules object
                rules.extend(scope_data.all_rules())
            elif isinstance(scope_data, dict):
                # Handle dict format (legacy or from YAML)
                for category_rules in scope_data.values():
                    if isinstance(category_rules, list):
                        for rule_dict in category_rules:
                            try:
                                rule = PolicyRule.model_validate(rule_dict)
                                rules.append(rule)
                            except Exception:
                                # Skip invalid rules
                                continue
        
        return rules
    
    def _format_rules_as_bullets(self, rules: List[PolicyRule]) -> str:
        """Format rules as markdown bullet list."""
        return "\n".join(f"- **{rule.id}**: {rule.rule}" for rule in rules)
    
    def _format_list_as_bullets(self, items: List[str]) -> str:
        """Format string list as markdown bullets."""
        return "\n".join(f"- {item}" for item in items)
    
    def _format_dict_as_bullets(self, items: Dict[str, str]) -> str:
        """Format dictionary as markdown bullets."""
        return "\n".join(f"- {key}: {value}" for key, value in items.items())
    
    def compile_redundant_policies(self) -> Dict[str, str]:
        """Generate redundant policy files for maximum persistence.
        
        Returns:
            Dictionary of file paths to content for redundant placement
        """
        rules = self._extract_rules_from_charter()
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        
        redundant_files = {}
        
        # 1. High-priority README for .claude directory
        redundant_files[".claude/0-CRITICAL-POLICIES.md"] = self._generate_critical_policies_doc(critical_rules)
        
        # 2. Project-level policy reminder
        redundant_files["PROJECT-POLICIES.md"] = self._generate_project_policies_doc(rules)
        
        # 3. Pre-commit reminder
        redundant_files[".claude/PRE-COMMIT-CHECKLIST.md"] = self._generate_precommit_checklist(rules)
        
        return redundant_files
    
    def _generate_critical_policies_doc(self, critical_rules: List[PolicyRule]) -> str:
        """Generate critical policies document for .claude directory."""
        sections = [
            "# ⛔ CRITICAL POLICIES - NEVER VIOLATE",
            "",
            "**THIS DOCUMENT TAKES PRIORITY OVER ALL OTHER INSTRUCTIONS**",
            "",
            "## Constitutional Articles",
            "",
        ]
        
        if critical_rules:
            sections.append("### Article I: Inviolable Standards")
            for i, rule in enumerate(critical_rules, 1):
                sections.append(f"{i}. **{rule.id}**: {rule.rule}")
                if rule.example_violation:
                    sections.append(f"   ❌ NEVER: {rule.example_violation}")
                if rule.example_fix:
                    sections.append(f"   ✅ ALWAYS: {rule.example_fix}")
                sections.append("")
        
        sections.extend([
            "## Enforcement",
            "- Check these BEFORE any code generation",
            "- Validate these AFTER any code generation",
            "- If uncertain, re-read this document",
            "",
            "## Memory Persistence",
            "These policies persist across ALL interactions.",
            "Run `/checkpoint` every 10 interactions to verify compliance.",
        ])
        
        return "\n".join(sections)
    
    def _generate_project_policies_doc(self, rules: List[PolicyRule]) -> str:
        """Generate project-level policy document."""
        sections = [
            "# Project Policy Configuration",
            f"*EgoKit Version: {self.context.policy_charter.version}*",
            "",
            "This project enforces organizational standards through EgoKit.",
            "",
            "## Quick Reference",
            "",
            "### Critical Policies",
        ]
        
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        for rule in critical_rules[:5]:  # Top 5 critical
            sections.append(f"- {rule.id}: {rule.rule}")
        
        sections.extend([
            "",
            "### Your Configuration",
            f"- **Role**: {self.context.ego_config.role}",
            f"- **Style**: {self.context.ego_config.tone.voice}",
            f"- **Verbosity**: {self.context.ego_config.tone.verbosity}",
            "",
            "### Commands",
            "- `/checkpoint` - Verify policy memory",
            "- `/refresh-policies` - Reload configuration",
            "- `/before-code` - Pre-code checklist",
            "",
            "## Full Details",
            "See CLAUDE.md for complete policy documentation.",
        ])
        
        return "\n".join(sections)
    
    def _generate_precommit_checklist(self, rules: List[PolicyRule]) -> str:
        """Generate pre-commit checklist document."""
        sections = [
            "# Pre-Commit Policy Checklist",
            "",
            "**Run through this checklist before EVERY commit**",
            "",
            "## Security Checks",
        ]
        
        security_rules = [r for r in rules if "security" in (r.tags or [])]
        for rule in security_rules[:3]:
            sections.append(f"- [ ] {rule.rule}")
        
        sections.extend([
            "",
            "## Code Quality",
        ])
        
        quality_rules = [r for r in rules if r.severity == Severity.WARNING]
        for rule in quality_rules[:3]:
            sections.append(f"- [ ] {rule.rule}")
        
        sections.extend([
            "",
            "## Validation",
            "- [ ] Run `/validate` command",
            "- [ ] All tests pass",
            "- [ ] No policy violations",
            "",
            "## Reminder",
            "If any item fails, fix it before committing.",
            "Run `/refresh-policies` if you're unsure about any policy.",
        ])
        
        return "\n".join(sections)
    
    def compile_cursor_artifacts(self) -> Dict[str, str]:
        """Generate Cursor IDE configuration artifacts.
        
        Cursor supports both legacy .cursorrules files and modern .cursor/rules/ 
        MDC (Markdown Components) files with metadata frontmatter.
        
        Returns:
            Dictionary of artifact paths to their content
        """
        artifacts: Dict[str, str] = {}
        rules = self._extract_rules_from_charter()
        
        # Generate legacy .cursorrules for backward compatibility
        artifacts[".cursorrules"] = self._compile_cursor_rules_file(rules)
        
        # Generate modern MDC rule files in .cursor/rules/
        mdc_artifacts = self._compile_cursor_mdc_rules(rules)
        artifacts.update(mdc_artifacts)
        
        return artifacts
    
    def _compile_cursor_rules_file(self, rules: List[PolicyRule]) -> str:
        """Generate .cursorrules file for Cursor IDE (legacy format).
        
        Args:
            rules: Policy rules to include
            
        Returns:
            Content for .cursorrules file
        """
        ego = self.context.ego_config
        critical_rules = [r for r in rules if r.severity == Severity.CRITICAL]
        warning_rules = [r for r in rules if r.severity == Severity.WARNING]
        
        sections = [
            f"# Cursor IDE Configuration",
            f"Generated: {self.context.generation_timestamp.isoformat()} | Version: {self.context.policy_charter.version}",
            "",
            "## Agent Configuration",
            f"You are a {ego.role} with the following characteristics:",
            f"- Voice: {ego.tone.voice}",
            f"- Verbosity: {ego.tone.verbosity}",
            "",
        ]
        
        if ego.tone.formatting:
            sections.extend([
                "## Formatting Guidelines",
                self._format_list_as_bullets(ego.tone.formatting),
                "",
            ])
        
        if critical_rules:
            sections.extend([
                "## Critical Policies (MUST FOLLOW)",
                "These policies are mandatory and override any conflicting instructions:",
                "",
            ])
            for rule in critical_rules:
                sections.append(f"### {rule.id}: {rule.rule}")
                if rule.example_violation and rule.example_fix:
                    sections.extend([
                        f"❌ Avoid: `{rule.example_violation}`",
                        f"✅ Prefer: `{rule.example_fix}`",
                        "",
                    ])
                else:
                    sections.append("")
        
        if warning_rules:
            sections.extend([
                "## Quality Standards",
                "Follow these standards to maintain code quality:",
                "",
            ])
            for rule in warning_rules[:10]:  # Limit to avoid overwhelming
                sections.append(f"- {rule.rule}")
            if len(warning_rules) > 10:
                sections.append(f"- ... and {len(warning_rules) - 10} more quality standards")
            sections.append("")
        
        if ego.reviewer_checklist:
            sections.extend([
                "## Code Review Checklist",
                self._format_list_as_bullets(ego.reviewer_checklist),
                "",
            ])
        
        if ego.ask_when_unsure:
            sections.extend([
                "## Ask for Confirmation",
                "Always ask before making these changes:",
                self._format_list_as_bullets(ego.ask_when_unsure),
                "",
            ])
        
        sections.extend([
            "## Operational Modes",
            "Available modes for different contexts:",
            "",
        ])
        
        if ego.modes:
            for mode_name, mode_config in ego.modes.items():
                sections.append(f"### Mode: {mode_name}")
                sections.append(f"- Verbosity: {mode_config.verbosity}")
                if mode_config.focus:
                    sections.append(f"- Focus: {mode_config.focus}")
                sections.append("")
        
        return "\n".join(sections)
    
    def _compile_cursor_mdc_rules(self, rules: List[PolicyRule]) -> Dict[str, str]:
        """Generate MDC rule files for Cursor's modern configuration system.
        
        MDC files support frontmatter metadata for priority, scope, and other settings.
        
        Args:
            rules: Policy rules to compile
            
        Returns:
            Dictionary of MDC file paths to their content
        """
        mdc_files: Dict[str, str] = {}
        
        # Group rules by category based on tags
        security_rules = [r for r in rules if "security" in (r.tags or [])]
        quality_rules = [r for r in rules if r.severity == Severity.WARNING]
        doc_rules = [r for r in rules if "documentation" in (r.tags or []) or "docs" in (r.tags or [])]
        
        # Generate security rules MDC if we have security rules
        if security_rules:
            mdc_files[".cursor/rules/security-policies.mdc"] = self._compile_mdc_rule_file(
                title="Security Policies",
                description="Critical security requirements that must be followed",
                priority="high",
                rules=security_rules
            )
        
        # Generate quality standards MDC if we have quality rules
        if quality_rules:
            mdc_files[".cursor/rules/quality-standards.mdc"] = self._compile_mdc_rule_file(
                title="Quality Standards",
                description="Code quality guidelines and best practices",
                priority="medium",
                rules=quality_rules
            )
        
        # Generate documentation rules MDC if we have doc rules
        if doc_rules:
            mdc_files[".cursor/rules/documentation-standards.mdc"] = self._compile_mdc_rule_file(
                title="Documentation Standards",
                description="Requirements for code documentation and comments",
                priority="medium",
                rules=doc_rules
            )
        
        # Always generate team conventions MDC
        ego = self.context.ego_config
        mdc_files[".cursor/rules/team-conventions.mdc"] = self._compile_team_conventions_mdc(ego)
        
        return mdc_files
    
    def _compile_mdc_rule_file(
        self, 
        title: str, 
        description: str, 
        priority: str, 
        rules: List[PolicyRule]
    ) -> str:
        """Generate an MDC rule file with frontmatter and content.
        
        Args:
            title: Rule file title
            description: Rule file description
            priority: Priority level (high, medium, low)
            rules: Policy rules to include
            
        Returns:
            MDC file content with frontmatter
        """
        sections = [
            "---",
            f"title: {title}",
            f"description: {description}",
            f"priority: {priority}",
            f'scope: "**/*.{{js,ts,py,java,go,rs,cpp,c,h}}"',
            "---",
            "",
            f"# {title}",
            "",
            description,
            "",
        ]
        
        # Group by severity
        critical = [r for r in rules if r.severity == Severity.CRITICAL]
        warning = [r for r in rules if r.severity == Severity.WARNING]
        
        if critical:
            sections.extend([
                "## Critical Requirements",
                "",
                "These must always be followed:",
                "",
            ])
            for rule in critical:
                sections.append(f"### {rule.id}")
                sections.append(rule.rule)
                sections.append("")
                if rule.example_violation and rule.example_fix:
                    sections.extend([
                        "**Example:**",
                        f"- ❌ Incorrect: `{rule.example_violation}`",
                        f"- ✅ Correct: `{rule.example_fix}`",
                        "",
                    ])
        
        if warning:
            sections.extend([
                "## Best Practices",
                "",
                "Follow these guidelines for quality code:",
                "",
            ])
            for rule in warning[:15]:  # Limit to avoid overwhelming
                sections.append(f"- **{rule.id}**: {rule.rule}")
            if len(warning) > 15:
                sections.append(f"- ... and {len(warning) - 15} more best practices")
            sections.append("")
        
        return "\n".join(sections)
    
    def _compile_team_conventions_mdc(self, ego: EgoConfig) -> str:
        """Generate team conventions MDC file from ego configuration.
        
        Args:
            ego: Ego configuration with team preferences
            
        Returns:
            MDC file content for team conventions
        """
        sections = [
            "---",
            "title: Team Conventions",
            "description: Organization-specific coding conventions and practices",
            "priority: high",
            'scope: "**/*"',
            "---",
            "",
            "# Team Conventions",
            "",
            f"## Your Role",
            f"You are a {ego.role} working on this codebase.",
            "",
            f"## Communication Style",
            f"- Voice: {ego.tone.voice}",
            f"- Verbosity: {ego.tone.verbosity}",
            "",
        ]
        
        if ego.defaults:
            sections.extend([
                "## Development Defaults",
            ])
            # Handle defaults as either dict or object attributes
            if isinstance(ego.defaults, dict):
                for key, value in ego.defaults.items():
                    formatted_key = key.replace('_', ' ').title()
                    sections.append(f"- {formatted_key}: {value}")
            else:
                # If defaults has attributes (not a dict)
                if hasattr(ego.defaults, 'structure'):
                    sections.append(f"- Structure: {ego.defaults.structure}")
                if hasattr(ego.defaults, 'code_style'):
                    sections.append(f"- Code Style: {ego.defaults.code_style}")
                if hasattr(ego.defaults, 'documentation'):
                    sections.append(f"- Documentation: {ego.defaults.documentation}")
                if hasattr(ego.defaults, 'testing'):
                    sections.append(f"- Testing: {ego.defaults.testing}")
            sections.append("")
        
        if ego.reviewer_checklist:
            sections.extend([
                "## Review Checklist",
                "",
                "When reviewing code, check for:",
                "",
            ])
            for item in ego.reviewer_checklist:
                sections.append(f"- {item}")
            sections.append("")
        
        if ego.ask_when_unsure:
            sections.extend([
                "## Require Confirmation",
                "",
                "Always ask before:",
                "",
            ])
            for item in ego.ask_when_unsure:
                sections.append(f"- {item}")
            sections.append("")
        
        return "\n".join(sections)


class ArtifactInjector:
    """Injects compiled artifacts into target repositories."""
    
    def __init__(self, target_repo: Path) -> None:
        """Initialize injector with target repository path.
        
        Args:
            target_repo: Path to target repository
        """
        self.target_repo = Path(target_repo)
    
    def inject_claude_artifacts(self, artifacts: Dict[str, str], preserve_manual: bool = True) -> None:
        """Inject comprehensive Claude Code artifacts into repository.
        
        Args:
            artifacts: Dictionary of artifact paths to their content
            preserve_manual: Whether to preserve manual sections
        """
        for artifact_path, content in artifacts.items():
            target_path = self.target_repo / artifact_path
            
            # Create parent directories if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._write_artifact(target_path, content, preserve_manual)
    
    def inject_claude_md(self, content: str, preserve_manual: bool = True) -> None:
        """Inject CLAUDE.md into repository root (legacy method).
        
        Args:
            content: Compiled CLAUDE.md content
            preserve_manual: Whether to preserve manual sections
        """
        target_path = self.target_repo / "CLAUDE.md"
        self._write_artifact(target_path, content, preserve_manual)
    
    def inject_claude_settings(self, content: str) -> None:
        """Inject .claude/settings.json into repository.
        
        Args:
            content: JSON settings content
        """
        target_path = self.target_repo / ".claude" / "settings.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
    
    def inject_claude_commands(self, commands: Dict[str, str]) -> None:
        """Inject custom slash commands into .claude/commands/ directory.
        
        Args:
            commands: Dictionary of command names to their content
        """
        commands_dir = self.target_repo / ".claude" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        for command_name, content in commands.items():
            command_path = commands_dir / f"{command_name}.md"
            command_path.write_text(content, encoding="utf-8")
    
    def inject_system_prompt_fragment(self, content: str) -> None:
        """Inject system prompt fragment for --append-system-prompt usage.
        
        Args:
            content: System prompt fragment content
        """
        fragment_dir = self.target_repo / ".claude" / "system-prompt-fragments"
        fragment_dir.mkdir(parents=True, exist_ok=True)
        
        fragment_path = fragment_dir / "egokit-policies.txt"
        fragment_path.write_text(content, encoding="utf-8")
    
    def inject_augment_artifacts(self, artifacts: Dict[str, str]) -> None:
        """Inject AugmentCode artifacts into repository.
        
        Args:
            artifacts: Dictionary mapping file paths to their content
        """
        for path, content in artifacts.items():
            file_path = self.target_repo / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
    
    def inject_augment_rules(
        self, 
        rules: List[PolicyRule], 
        ego_config: EgoConfig,
        preserve_manual: bool = True
    ) -> None:
        """Legacy method - Inject AugmentCode rules into .augment/rules/ directory.
        
        Args:
            rules: Policy rules to inject
            ego_config: Ego configuration for behavioral rules
            preserve_manual: Whether to preserve manual sections
        """
        augment_dir = self.target_repo / ".augment" / "rules"
        augment_dir.mkdir(parents=True, exist_ok=True)
        
        # Create context for compiler usage
        from .models import CompilationContext, PolicyCharter
        from datetime import datetime
        
        # Create minimal charter for compilation
        placeholder_charter = PolicyCharter(
            version="1.0.0",
            scopes={},
            metadata={}
        )
        
        context = CompilationContext(
            target_repo=self.target_repo,
            policy_charter=placeholder_charter,
            ego_config=ego_config,
            generation_timestamp=datetime.now()
        )
        
        # Create temporary compiler instance
        compiler = ArtifactCompiler(context)
        
        # Create policy rules file
        policy_content = compiler._compile_augment_policy_rules(rules)
        policy_path = augment_dir / "policy-rules.md"
        self._write_artifact(policy_path, policy_content, preserve_manual)
        
        # Create ego/behavioral rules file
        ego_content = compiler._compile_augment_ego_rules(ego_config)
        ego_path = augment_dir / "coding-style.md"
        self._write_artifact(ego_path, ego_content, preserve_manual)
    
    def inject_ego_card(self, content: str, preserve_manual: bool = True) -> None:
        """Inject EGO.md into repository root.
        
        Args:
            content: Compiled ego card content
            preserve_manual: Whether to preserve manual sections
        """
        target_path = self.target_repo / "EGO.md"
        self._write_artifact(target_path, content, preserve_manual)
    
    def inject_cursor_artifacts(
        self, 
        artifacts: Dict[str, str], 
        preserve_manual: bool = True
    ) -> None:
        """Inject Cursor IDE artifacts into repository.
        
        Handles both legacy .cursorrules and modern .cursor/rules/ MDC files.
        
        Args:
            artifacts: Dictionary of artifact paths to their content
            preserve_manual: Whether to preserve manual sections in existing files
        """
        for artifact_path, content in artifacts.items():
            target_path = self.target_repo / artifact_path
            
            # Create parent directories if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the artifact
            if artifact_path.endswith('.mdc') or artifact_path == '.cursorrules':
                # For rule files, preserve manual sections
                self._write_artifact(target_path, content, preserve_manual)
            else:
                # For other files, just write directly
                target_path.write_text(content, encoding="utf-8")
    
    def _write_artifact(
        self, 
        target_path: Path, 
        content: str, 
        preserve_manual: bool
    ) -> None:
        """Write artifact to target path with optional manual section preservation.
        
        Args:
            target_path: Where to write the artifact
            content: Content to write
            preserve_manual: Whether to preserve existing manual sections
        """
        if preserve_manual and target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8")
            content = self._merge_with_manual_sections(content, existing_content)
        
        target_path.write_text(content, encoding="utf-8")
    
    def _merge_with_manual_sections(
        self, 
        new_content: str, 
        existing_content: str
    ) -> str:
        """Merge new content with preserved manual sections.
        
        Args:
            new_content: Newly compiled content
            existing_content: Existing file content
            
        Returns:
            Merged content with manual sections preserved
        """
        # Look for manual sections marked with <!-- MANUAL --> comments
        import re
        
        manual_sections = []
        pattern = r"<!-- MANUAL:START -->(.*?)<!-- MANUAL:END -->"
        
        for match in re.finditer(pattern, existing_content, re.DOTALL):
            manual_sections.append(match.group(1).strip())
        
        if manual_sections:
            new_content += "\n\n---\n## Manual Project Notes\n\n"
            new_content += "\n\n".join(manual_sections)
        
        return new_content