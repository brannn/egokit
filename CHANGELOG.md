# Changelog

All notable changes to EgoKit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-11-29

### Added
- **Session Protocol**: New `session:` block in charter.yaml for context continuity across AI agent sessions
- `SessionConfig`, `SessionStartup`, `SessionShutdown`, and `ContextFile` models for session configuration
- Session Protocol section in AGENTS.md output (opt-in, only when `session:` block is present)
- `/ego-refresh` now includes session startup checklist when session protocol is configured
- `/ego-checkpoint` now includes session handoff mode with progress file template
- Hint in `/ego-refresh` when session protocol is not configured (discoverability)
- Commented-out `session:` block example in default charter.yaml from `ego init`
- "Modifying Policies" section in AGENTS.md pointing to charter.yaml for AI agent discoverability
- Self-documenting comments in charter.yaml template (schema reference, severity levels, scopes)

### Changed
- `PolicyCharter` model now accepts optional `session` field
- `/ego-checkpoint` description updated to "Pre-change compliance snapshot or session handoff"

## [1.0.2] - 2025-11-27

### Added
- `/ego-persona` command to switch between distinct working personas
- Four personas: developer (default), writer, reviewer, architect
- Writer persona references DOCUMENTATION.md guidelines for technical writing tasks

### Changed
- Now generates 9 slash commands (added ego-persona)
- Updated README.md, USER_GUIDE.md, and AGENTS.md with new command

## [1.0.1] - 2025-11-27

### Changed
- `/ego-security` command now scopes analysis to specified file or staged changes only
- Reduced security checklist from 6 dimensions to 3 high-priority items
- Added 60-second execution target to improve response time
- Updated USER_GUIDE.md and README.md with revised command description

## [1.0.0] - 2025-11-26

Major architectural refactor: EgoKit is now a stateless compiler that generates
AGENTS.md files and slash commands for AI coding tools.

### Added
- AGENTS.md as the universal output format for all AI coding agents
- Hybrid ownership model with marker-based sections (`<!-- BEGIN-EGOKIT-POLICIES -->`)
- Eight `ego-*` slash commands as pure AI prompts (no CLI invocation required)
- `SYSTEM_ARCHITECTURE.md` documenting technical internals
- `USER_GUIDE.md` with comprehensive usage examples
- Python 3.13 support with UV package manager

### Changed
- EgoKit is now a pure compiler, not a runtime validator
- AI agents interpret and enforce policies by reading AGENTS.md directly
- `watch` command detects AGENTS.md instead of CLAUDE.md
- Modern Python typing syntax throughout (`list`, `dict`, `|` unions)
- All ruff warnings resolved across codebase

### Removed
- `validate` CLI command (validation is now AI-interpreted)
- `--agent` flag and multi-agent code paths
- `src/egokit/validator.py` module
- `src/egokit/detectors/` directory and all detector infrastructure
- `install-egokit.sh` (use `uv sync --dev` instead)
- `pytest.ini` (configuration moved to pyproject.toml)
- Legacy artifact formats: CLAUDE.md, EGO.md, PROJECT-POLICIES.md

### Fixed
- Consistent code style with ruff compliance

## [0.3.0] - 2025-01-09

### Added
- Fresh repository with clean commit history
- Multi-agent support with `--agent` CLI parameter
- Cursor IDE integration with `.cursorrules` format
- `VERSIONING.md` documenting semantic versioning strategy

### Changed
- Repository restructured with single initial commit
- Migrated from deprecated Pydantic methods

## [0.1.0] - 2024-01-08

### Added
- Initial release of EgoKit
- Policy registry system with hierarchical scopes
- Claude Code artifact generation
- CLI commands: init, apply, validate, doctor
- Policy charter and ego configuration schemas

[1.1.0]: https://github.com/brannn/egokit/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/brannn/egokit/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/brannn/egokit/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/brannn/egokit/compare/v0.3.14...v1.0.0
[0.3.0]: https://github.com/brannn/egokit/compare/v0.1.0...v0.3.0
[0.1.0]: https://github.com/brannn/egokit/releases/tag/v0.1.0