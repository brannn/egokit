# EgoKit User Guide

This guide provides comprehensive documentation for configuring and using EgoKit to manage AI coding agent policies across your organization.

## Table of Contents

- [Installation and Setup](#installation-and-setup)
- [Creating a Policy Registry](#creating-a-policy-registry)
- [Writing Charter Rules](#writing-charter-rules)
- [Writing Ego Configurations](#writing-ego-configurations)
- [Running ego apply](#running-ego-apply)
- [Customizing AGENTS.md](#customizing-agentsmd)
- [Slash Command Reference](#slash-command-reference)
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
│       └── ego-suggest.md
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

