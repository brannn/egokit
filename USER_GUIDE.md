# EgoKit User Guide

This guide provides comprehensive documentation for configuring and using EgoKit to manage AI coding agent policies across your organization.

## Table of Contents

- [Installation and Setup](#installation-and-setup)
- [Creating a Policy Registry](#creating-a-policy-registry)
- [Writing Charter Rules](#writing-charter-rules)
- [Writing Ego Configurations](#writing-ego-configurations)
- [Running ego apply](#running-ego-apply)
- [Customizing AGENTS.md](#customizing-agentsmd)
- [Session Protocol](#session-protocol)
- [Slash Command Reference](#slash-command-reference)
- [Learning from Corrections (Imprint)](#learning-from-corrections-imprint)
- [Troubleshooting](#troubleshooting)

## Installation and Setup

EgoKit requires Python 3.13 or later. Install using UV (recommended) or pip:

```bash
# Using UV (recommended)
uv add egokit

# Or using pip
pip install egokit
```

Verify the installation:

```bash
ego --version
```

For development work on EgoKit itself, clone the repository and install with UV:

```bash
git clone https://github.com/brannn/egokit.git
cd egokit
uv sync --dev
```

## Creating a Policy Registry

A policy registry is the source of truth for your organizational standards. It contains two primary configuration files: the charter (policy rules) and the ego configuration (AI behavior settings).

### Initializing a New Registry

Create a new policy registry using the init command:

```bash
ego init --path /path/to/config-repo --org "Your Organization Name"
```

This generates the following structure:

```
.egokit/policy-registry/
├── charter.yaml
├── ego/
│   ├── global.yaml
│   └── teams/
└── schemas/
    ├── charter.schema.json
    └── ego.schema.json
```

The registry should be version controlled and shared across your organization. Teams clone or reference this registry when applying policies to their project repositories.

### Registry Location

EgoKit searches for the policy registry in these locations, in order:

1. Path specified by `--registry` option
2. `.egokit/policy-registry/` in current directory
3. `.egokit/policy-registry/` in parent directories (walking up to root)

## Writing Charter Rules

The charter.yaml file defines enforceable policy rules. Each rule specifies what to check and how severe violations are. AI coding agents interpret and enforce these rules.

### Charter Structure

```yaml
version: 1.0.0
scopes:
  global:
    security:
      - id: SEC-001
        rule: "Never commit credentials, API keys, or secrets to version control"
        severity: critical
        tags:
          - security
          - secrets
      - id: SEC-002
        rule: "Validate all external input before processing"
        severity: critical
        tags:
          - security
    code_quality:
      - id: QUAL-001
        rule: "All public functions must have docstrings"
        severity: warning
        tags:
          - documentation
          - quality
metadata:
  description: "Policy charter for Your Organization"
  maintainer: "platform-team@example.com"
```

### Severity Levels

Rules use three severity levels that determine how they appear in AGENTS.md:

| Severity | Section Header | Meaning |
|----------|---------------|---------|
| critical | Critical (Must Follow) | Violations block work and require immediate attention |
| warning | Required (Should Follow) | Violations should be addressed but do not block |
| info | Recommended | Guidance for best practices |

### Scope Hierarchy

EgoKit supports hierarchical scopes with the following precedence (later overrides earlier):

```
global < team < project < user < session
```

Define team-specific rules by adding scope sections:

```yaml
scopes:
  global:
    security:
      - id: SEC-001
        rule: "Base security rule"
        severity: critical
  teams/backend:
    security:
      - id: SEC-001
        rule: "Backend-specific security rule (overrides global)"
        severity: critical
```

## Writing Ego Configurations

The ego configuration controls AI agent behavior, including communication style, verbosity, and operational personas.

### Global Configuration

The global.yaml file establishes organization-wide defaults:

```yaml
version: 1.0.0
ego:
  role: "Senior Software Engineer"
  tone:
    voice: professional
    verbosity: balanced
  defaults:
    structure: clean
    comments: minimal
  personas:
    implementer:
      focus: implementation
      verbosity: concise
    reviewer:
      focus: analysis
      verbosity: detailed
    security:
      focus: security
      verbosity: thorough
```

### Team Overrides

Create team-specific configurations in the `ego/teams/` directory:

```yaml
# ego/teams/backend.yaml
version: 1.0.0
ego:
  role: "Backend Engineer"
  tone:
    voice: technical
    verbosity: concise
  defaults:
    language: python
    framework: fastapi
```

Team configurations merge with global settings. Specified values override global defaults while unspecified values inherit from global.

## Running ego apply

The apply command compiles your policy registry into artifacts that AI coding tools consume.

### Basic Usage

Apply policies to a target repository:

```bash
ego apply --repo /path/to/project --registry /path/to/policy-registry
```

If the registry is in a parent directory, EgoKit discovers it automatically:

```bash
cd /path/to/project
ego apply
```

### Preview Mode

Use dry-run to see what would be generated without writing files:

```bash
ego apply --dry-run
```

This displays the content of AGENTS.md and all slash commands to stdout.

### Force Mode

When an existing AGENTS.md lacks EgoKit markers, the apply command prompts for confirmation before appending content. Use the force flag to skip this prompt:

```bash
ego apply --force
```

### Output Location

The apply command generates files in the target repository:

```
project/
├── AGENTS.md
├── .claude/
│   └── commands/
│       ├── ego-validate.md
│       ├── ego-rules.md
│       ├── ego-checkpoint.md
│       ├── ego-review.md
│       ├── ego-security.md
│       ├── ego-refresh.md
│       ├── ego-stats.md
│       ├── ego-suggest.md
│       └── ego-persona.md
└── .augment/
    └── commands/
        └── (identical commands)
```

## Customizing AGENTS.md

EgoKit uses a hybrid ownership model for AGENTS.md. You can add custom content before and after the EgoKit-managed section.

### Marker-Based Sections

EgoKit manages content between two HTML comment markers:

```markdown
# AGENTS.md

Your custom introduction here.

<!-- BEGIN-EGOKIT-POLICIES -->
(EgoKit generates this content)
<!-- END-EGOKIT-POLICIES -->

Your custom footer content here.
```

When you run `ego apply`, EgoKit replaces only the content between the markers. Content before and after the markers remains unchanged.

### New Projects

For new projects without an existing AGENTS.md, EgoKit generates a complete template with placeholder sections for your custom content.

### Existing Projects

If AGENTS.md exists without markers, EgoKit prompts before appending the managed section. Use `--force` to append without confirmation.

## Session Protocol

EgoKit supports session continuity protocols for maintaining context across AI agent sessions. This feature is opt-in and activated by adding a `session:` block to your charter.yaml.

### Why Session Protocols?

AI coding agents operate within context windows that eventually fill up or reset. Without explicit handoff protocols, work context is lost between sessions. Session protocols define what the agent should do when starting and ending work sessions to maintain continuity.

### Enabling Session Protocols

Add a `session:` block to your charter.yaml:

```yaml
version: 1.0.0
scopes:
  global:
    # ... your policy rules ...

session:
  startup:
    read: ["PROGRESS.md"]
    run: ["git status", "git log --oneline -5"]
  shutdown:
    update: ["PROGRESS.md"]
    commit: false
  progress_file: "PROGRESS.md"
```

### Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `startup.read` | Files to read for context at session start | `["PROGRESS.md"]` |
| `startup.run` | Commands to run for orientation | `["git status", "git log --oneline -5"]` |
| `shutdown.update` | Files to update before ending session | `["PROGRESS.md"]` |
| `shutdown.commit` | Whether to require committing changes | `false` |
| `progress_file` | Primary progress file path | `"PROGRESS.md"` |
| `context_files` | Explicit file configurations with modes | `[]` |

### Context File Modes

For projects that use multiple context files, you can specify update modes:

```yaml
session:
  context_files:
    - path: "PROGRESS.md"
      mode: append    # Add new entries (session log pattern)
    - path: "STATUS.md"
      mode: replace   # Update in place (current state pattern)
```

The `append` mode is for files like PROGRESS.md that accumulate session entries. The `replace` mode is for files like STATUS.md that represent current state.

### Generated Output

When session protocols are enabled, EgoKit generates:

1. **Session Protocol section in AGENTS.md** with startup and shutdown checklists
2. **Enhanced /ego-refresh** that includes session startup instructions
3. **Enhanced /ego-checkpoint** that includes session handoff mode with progress file template

### Progress File Template

The `/ego-checkpoint --handoff` command provides this template for updating progress files:

```markdown
## Session: YYYY-MM-DD

### Completed
- [What was accomplished this session]

### Next Steps
- [What remains to be done]
- [Priority order if applicable]

### Blockers
- [Any issues encountered]
- [Questions that need answers]

### Files Modified
- [List of files changed]
```

### Discoverability

If you haven't enabled session protocols, the `/ego-refresh` command includes a hint about the feature. The default charter.yaml from `ego init` also includes a commented-out session block as an example.

## Slash Command Reference

EgoKit generates eight slash commands that work identically in Claude Code and Augment.

### /ego-validate

Validates current work against policies defined in AGENTS.md. Use this command to check compliance before committing changes.

### /ego-rules

Displays active policy rules organized by severity. Use this to review what policies apply to the current project.

### /ego-checkpoint

Captures a compliance snapshot before making changes. This establishes a baseline for comparison after modifications.

### /ego-review

Runs a pre-commit review checklist. Use this before finalizing changes to ensure all policies are satisfied.

### /ego-security

Activates security-focused analysis mode. By default, analyzes only the specified file or staged changes to keep execution fast. Provide a file path for targeted review, or run without arguments to review staged changes.

### /ego-refresh

Re-reads AGENTS.md to prevent policy drift. Use this periodically during long sessions to ensure the agent maintains awareness of current policies.

### /ego-stats

Analyzes historical violation patterns from git history. Use this to identify recurring issues and inform policy updates.

### /ego-suggest

Proposes new rules based on codebase patterns. Use this to discover implicit standards that should become explicit policies.

### /ego-persona

Switches the AI agent to a distinct working persona. Available personas:

- **developer** (default): Implementation-focused with emphasis on code quality and testing
- **writer**: Technical documentation focus with emphasis on clarity, audience awareness, and DOCUMENTATION.md guidelines
- **reviewer**: Critical analysis mode focused on finding issues rather than fixing them
- **architect**: System-level thinking with emphasis on trade-offs, boundaries, and long-term implications

Use `/ego-persona writer` before documentation tasks, or `/ego-persona reviewer` when you want critical feedback without immediate fixes.

### /ego-imprint

Analyzes your session history to detect correction patterns and suggest policy rules. This command runs the `ego imprint` CLI tool to scan Claude Code and Augment session logs.

## Learning from Corrections (Imprint)

Over time, developers establish implicit preferences through repeated corrections to AI assistants. Phrases like "No, use snake_case not camelCase" or "Actually, always include type hints" represent policies that exist only in the developer's head. The Imprint feature detects these patterns and suggests explicit charter rules.

### How Imprint Works

The imprint command parses session logs from Claude Code and Augment, searching for correction patterns in your messages to the AI. It applies regex-based heuristics to identify three types of patterns:

**Explicit Corrections** occur when you directly correct the AI's output. Phrases beginning with "No,", "Actually,", "Instead,", or "Use X not Y" indicate a preference the AI violated. Imprint extracts these corrections and categorizes them by topic (code style, security, documentation, etc.).

**Style Preferences** are detected when you repeatedly request a particular style of interaction. Messages containing "be concise", "show code first", or "explain step by step" indicate communication preferences that could become ego configuration settings.

**Implicit Patterns** emerge from frequency analysis. If you frequently reference a particular policy ID or repeatedly make similar requests, Imprint identifies these as candidates for explicit rules.

### Running ego imprint

The basic command scans recent sessions and displays detected patterns:

```bash
ego imprint --since 30
```

This analyzes sessions from the last 30 days. The output shows correction patterns with occurrence counts and confidence levels.

To generate policy suggestions from detected patterns:

```bash
ego imprint --since 30 --suggest
```

For detailed evidence showing which messages triggered each pattern:

```bash
ego imprint --since 30 --suggest --explain
```

### Command Options

| Option | Description |
|--------|-------------|
| `--since DAYS` | Analyze sessions from the last N days (default: 30) |
| `--claude-logs PATH` | Path to Claude Code logs (default: ~/.claude/projects/) |
| `--augment-logs PATH` | Path to Augment session exports |
| `--suggest` | Generate policy suggestions from detected patterns |
| `--explain` | Show detailed evidence for each pattern |
| `--min-confidence LEVEL` | Filter by confidence level: low, medium, or high |

### Understanding the Output

The imprint command produces output in several sections:

**Session Summary** shows how many sessions were analyzed and from which sources (Claude Code, Augment).

**Correction Patterns** lists detected corrections with occurrence counts. Each pattern shows the original correction text, its category, and a confidence level based on how clearly it matches correction indicators.

**Style Preferences** shows detected communication preferences with occurrence counts.

**Suggested Rules** (when using `--suggest`) displays YAML snippets formatted for charter.yaml. Each suggestion includes the pattern that triggered it and an auto-generated rationale.

### Adding Suggested Rules

After reviewing suggestions, copy the YAML snippets into your charter.yaml file. Suggestions are formatted to match the charter schema:

```yaml
# Suggested rule from imprint:
- id: STYLE-001
  rule: "Use snake_case for all Python variable names"
  severity: warning
  rationale: "Detected from 5 corrections: 'No, use snake_case not camelCase'"
  tags:
    - code_style
    - python
```

Review and edit suggestions before adding them. Imprint provides starting points, not final policies. Adjust the rule text, severity, and tags to match your organization's standards.

You can use your AI coding assistant to help integrate suggestions into the policy registry. Share the imprint output with your assistant and ask it to review the suggestions, refine the rule text, assign appropriate severity levels, or merge similar patterns into consolidated rules. The assistant can also help identify conflicts with existing charter rules and suggest appropriate placement within the scope hierarchy. Since the assistant is already aware of the charter schema (from the registry's schemas/ directory), it can validate suggestions and ensure they conform to the expected structure.

After adding rules, run `ego apply` to regenerate AGENTS.md with the new policies.

### Log File Locations

Claude Code stores session logs in `~/.claude/projects/` organized by project path. Each session is a JSONL file containing message history.

Augment session exports are JSON files that you export manually from the Augment interface. Specify the directory containing these exports with `--augment-logs`.

## Troubleshooting

### Registry Not Found

If EgoKit cannot locate your policy registry, specify the path explicitly:

```bash
ego apply --registry /path/to/policy-registry
```

Verify the registry exists and contains charter.yaml.

### Schema Validation Errors

Charter and ego configuration files must conform to their JSON schemas. Common issues include missing required fields, invalid severity values, or malformed YAML syntax.

Run the doctor command to validate your configuration:

```bash
ego doctor --registry /path/to/policy-registry
```

### Marker Conflicts

If AGENTS.md contains malformed markers (only begin or only end, or markers in wrong order), EgoKit treats the file as having no markers. Fix the markers manually or delete the file and regenerate.

### Permission Errors

EgoKit creates directories and files in the target repository. Ensure write permissions for the .claude/, .augment/, and AGENTS.md locations.

