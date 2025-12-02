# EgoKit System Architecture

This document describes the internal design and implementation of EgoKit for contributors and users interested in understanding how the system works.

## Table of Contents

- [Design Philosophy](#design-philosophy)
- [Data Flow](#data-flow)
- [Module Overview](#module-overview)
- [Compilation Pipeline](#compilation-pipeline)
- [Hybrid Ownership Model](#hybrid-ownership-model)
- [Extension Points](#extension-points)

## Design Philosophy

EgoKit follows a compiler model rather than a runtime model. This distinction shapes every architectural decision.

A runtime tool would execute during development, intercepting requests, validating code, and enforcing policies in real time. Such tools require installation in each project, background processes, and integration hooks.

EgoKit instead operates as a build-time compiler. It reads policy configuration files, transforms them into AI-native artifacts, and writes those artifacts to disk. The AI coding tools (Claude Code, Augment, Cursor) read these artifacts during their normal operation. EgoKit has no runtime presence.

This approach offers several advantages. The generated artifacts are plain text files that can be inspected, version controlled, and modified. No background process consumes resources. No network calls occur during development. The system works offline and requires no authentication or external services.

The compiler model also enables a clean separation of concerns. EgoKit is responsible for policy compilation. AI coding tools are responsible for policy interpretation and enforcement. Each component does one thing well.

## Data Flow

The compilation process follows a linear data flow:

```
Policy Registry → Compiler → Artifacts
     (input)       (transform)   (output)
```

### Input: Policy Registry

The policy registry consists of YAML configuration files organized in a standard directory structure:

```
.egokit/policy-registry/
├── charter.yaml          # Policy rules
├── ego/
│   ├── global.yaml       # Global behavior settings
│   └── teams/            # Team-specific overrides
└── schemas/              # JSON Schema validation
```

The charter defines what policies exist. The ego configuration defines how the AI should behave when applying those policies.

### Transform: Compilation

The compiler loads the registry, validates against schemas, merges hierarchical scopes, and generates output content. The compilation is deterministic: the same input always produces the same output.

### Output: Artifacts

The compiler produces two categories of artifacts:

1. AGENTS.md - A markdown file containing policy rules organized by severity, behavioral guidelines, and security considerations.

2. Slash commands - Markdown files in .claude/commands/ and .augment/commands/ that provide interactive policy reinforcement.

## Module Overview

EgoKit consists of five primary modules:

### cli.py

The command-line interface module implements the ego command with subcommands for init, apply, doctor, and watch. It handles argument parsing, registry discovery, and user interaction.

Key responsibilities:
- Parse command-line arguments using Typer
- Discover policy registry location
- Coordinate compilation and artifact injection
- Handle user prompts for confirmation

### compiler.py

The artifact compiler transforms policy configuration into output content. This module contains the core compilation logic.

Key responsibilities:
- Load and merge charter rules by scope
- Load and merge ego configurations by scope
- Generate AGENTS.md content with proper section structure
- Generate slash command content with frontmatter
- Manage marker-based section injection

### registry.py

The registry module handles loading and validating policy configuration files.

Key responsibilities:
- Load charter.yaml and parse policy rules
- Load ego configuration files and merge hierarchically
- Validate configuration against JSON schemas
- Resolve scope precedence

### models.py

The models module defines data structures for policy configuration using Pydantic.

Key types:
- PolicyRule - A single enforceable rule with id, text, severity, and tags
- PolicyCharter - The complete charter configuration
- EgoConfig - AI behavior configuration
- CompilationContext - All inputs needed for compilation

### imprint/

The imprint module analyzes AI session logs to detect correction patterns and generate policy suggestions. This module operates independently from the compilation pipeline, providing a feedback loop from actual usage back to policy definitions.

The module contains four components:

**models.py** defines data structures for session analysis: Message and Session represent parsed log entries, while CorrectionPattern, StylePreference, and ImplicitPattern represent detected patterns.

**parsers.py** handles log format parsing. The ClaudeCodeParser processes JSONL files from Claude Code sessions stored in ~/.claude/projects/. The AugmentParser processes JSON exports from Augment sessions. Both parsers normalize logs into a common Session structure.

**detector.py** implements pattern detection using regex-based heuristics. The PatternDetector scans user messages for correction indicators ("No, use X not Y", "Actually, I meant..."), style preferences ("be concise", "show code first"), and implicit patterns (frequently referenced policy IDs). Detection uses occurrence counting and confidence scoring rather than ML or embeddings.

**suggester.py** transforms detected patterns into charter.yaml rule suggestions. The PolicySuggester maps patterns to the charter schema, generating YAML snippets with appropriate severity levels and rationale text.

The data flow follows a three-phase pipeline:

```
Session Logs → Parsers → Sessions → Detector → Patterns → Suggester → YAML
```

## Compilation Pipeline

The compilation pipeline transforms policy configuration into output artifacts through several stages.

### Stage 1: Registry Loading

The registry module loads charter.yaml and ego configuration files. Each file is validated against its JSON schema. Invalid configuration produces clear error messages identifying the problem location.

### Stage 2: Scope Merging

Rules and configurations from multiple scopes are merged according to precedence. The precedence order from lowest to highest is: global, team, project, user, session. When rules share the same ID, higher-precedence scopes override lower ones.

### Stage 3: Rule Organization

The compiler organizes rules by severity and category. Critical rules appear in the "Critical (Must Follow)" section. Warning rules appear in "Required (Should Follow)". Info rules appear in "Recommended". Security-tagged rules receive additional treatment in a dedicated Security Considerations section.

### Stage 4: Content Generation

The compiler generates markdown content for AGENTS.md and each slash command. AGENTS.md receives the complete policy content with proper section headers. Slash commands receive focused prompts that reference AGENTS.md for policy details.

### Stage 5: Artifact Injection

The generated content is written to the target repository. For AGENTS.md, the compiler respects the hybrid ownership model by preserving human content outside the managed markers. For slash commands, files are written to both .claude/commands/ and .augment/commands/.

## Hybrid Ownership Model

AGENTS.md uses a marker-based system that enables shared ownership between EgoKit and human authors.

### Markers

Two HTML comments define the EgoKit-managed region:

```markdown
<!-- BEGIN-EGOKIT-POLICIES -->
(generated content)
<!-- END-EGOKIT-POLICIES -->
```

Content before the begin marker and after the end marker belongs to the human author. EgoKit preserves this content during updates.

### Update Scenarios

When apply runs, it handles three scenarios:

1. No existing AGENTS.md - Generate complete template with markers and placeholder sections for human content.

2. Existing AGENTS.md with markers - Replace content between markers, preserve content outside markers.

3. Existing AGENTS.md without markers - Prompt for confirmation (or use --force), then append the managed section with markers.

### Implementation

The compiler module provides helper functions for marker management:

- find_egokit_section() - Locate marker positions in existing content
- extract_human_content() - Extract content before and after markers
- inject_egokit_section() - Insert or replace the managed section

## Extension Points

EgoKit provides several extension points for customization.

### Adding Slash Commands

New slash commands can be added by extending the compile_slash_commands method in ArtifactCompiler. Each command requires a name and content. The content should reference AGENTS.md rather than containing policy details directly.

### New Scope Levels

Additional scope levels can be added to the precedence hierarchy by modifying the scope merging logic in the registry module. New scopes must have corresponding configuration file locations.

### Alternative Output Formats

The compiler generates markdown output. Alternative formats (JSON, YAML, or tool-specific configurations) can be added by implementing new compilation methods that transform the same CompilationContext into different output structures.

