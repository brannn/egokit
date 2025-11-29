# EgoKit

[![PyPI version](https://img.shields.io/pypi/v/egokit.svg)](https://pypi.org/project/egokit/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

EgoKit is a stateless, file-based compiler that transforms organizational policies into AGENTS.md content and AI-native slash command prompts. EgoKit generates the rules; modern AI coding tools interpret and execute them.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Generated Artifacts](#generated-artifacts)
- [Further Reading](#further-reading)

## Overview

EgoKit addresses a fundamental challenge with AI coding assistants: they forget organizational standards between sessions and sometimes within the same conversation. Teams repeatedly re-explain the same requirements while each developer's AI produces code that drifts from established patterns.

EgoKit solves this by compiling your organization's policies into artifacts that AI coding tools consume natively. You define your standards once in a policy registry. EgoKit compiles them into AGENTS.md (the emerging standard for AI agent configuration) and a set of slash commands that reinforce those policies during development sessions.

The compilation model means EgoKit has no runtime component. It reads your policy files, generates output artifacts, and exits. The AI coding tools (Claude Code, Augment, Cursor, and others) read those artifacts and enforce your policies during their normal operation.

## Installation

EgoKit requires Python 3.13 or later.

```bash
# Using UV (recommended)
uv add egokit

# Or using pip
pip install egokit
```

For development installation:

```bash
git clone https://github.com/brannn/egokit.git
cd egokit
uv sync --dev
```

## Quick Start

Initialize a policy registry in your organization's configuration repository:

```bash
ego init --org "Your Organization"
```

This creates the policy registry structure:

```
.egokit/policy-registry/
├── charter.yaml          # Policy rules with severity and detectors
├── ego/
│   ├── global.yaml       # Organization-wide AI behavior settings
│   └── teams/            # Team-specific overrides
└── schemas/              # JSON Schema validation files
```

Define your policies in the charter and ego configuration files, then apply them to any project repository:

```bash
ego apply --repo /path/to/project --registry /path/to/policy-registry
```

After generating the initial registry, use your AI coding assistant to refine the charter rules and ego settings based on your team's specific requirements. You can use your AI assistant to help develop and maintain these files once it is aware of the EgoKit schema in the registry's schemas/ directory.

EgoKit generates AGENTS.md and slash commands in the target repository. AI coding tools read these files automatically.

For detailed configuration examples and advanced usage, see the [User Guide](USER_GUIDE.md).

## Command Reference

| Command | Description |
|---------|-------------|
| `ego init` | Create a new policy registry with starter templates |
| `ego apply` | Compile policies into AGENTS.md and slash commands |
| `ego doctor` | Display current policy configuration and validation status |
| `ego watch` | Monitor registry for changes and recompile automatically |

### Common Options

The `apply` command accepts these options:

| Option | Description |
|--------|-------------|
| `--repo PATH` | Target repository for generated artifacts |
| `--registry PATH` | Source policy registry location |
| `--dry-run` | Preview generated content without writing files |
| `--force` | Overwrite existing AGENTS.md without confirmation |

## Generated Artifacts

EgoKit produces two categories of output:

### AGENTS.md

The primary configuration file that AI coding tools read to understand your organizational policies. AGENTS.md contains policy rules organized by severity, behavioral guidelines, and security considerations. EgoKit manages a fenced section within AGENTS.md, allowing you to maintain custom content before and after the generated policies.

### Slash Commands

EgoKit generates eight slash commands in both `.claude/commands/` and `.augment/commands/` directories:

| Command | Purpose |
|---------|---------|
| `/ego-validate` | Check current work against policies defined in AGENTS.md |
| `/ego-rules` | Display active policy rules and their severity levels |
| `/ego-checkpoint` | Capture compliance state before making changes |
| `/ego-review` | Run pre-commit review checklist |
| `/ego-security` | Security-focused review of specified file or staged changes |
| `/ego-refresh` | Re-read AGENTS.md to prevent policy drift |
| `/ego-stats` | Analyze historical violation patterns |
| `/ego-suggest` | Propose new rules based on codebase patterns |
| `/ego-persona` | Switch working persona (developer, writer, reviewer, architect) |

These commands are pure AI prompts that reference AGENTS.md. They contain no CLI invocations and work identically across Claude Code and Augment.

### Session Protocol (Optional)

EgoKit supports session continuity protocols for maintaining context across AI agent sessions. Add a `session:` block to your charter.yaml to enable:

```yaml
session:
  startup:
    read: ["PROGRESS.md"]
    run: ["git status", "git log --oneline -5"]
  shutdown:
    update: ["PROGRESS.md"]
    commit: false
```

When enabled, EgoKit generates a Session Protocol section in AGENTS.md with startup and shutdown checklists. The `/ego-refresh` and `/ego-checkpoint` commands also include session-specific instructions.

See the [User Guide](USER_GUIDE.md) for detailed session protocol configuration.

## Further Reading

- [User Guide](USER_GUIDE.md) - Comprehensive usage examples and configuration reference
- [System Architecture](SYSTEM_ARCHITECTURE.md) - Technical internals for contributors