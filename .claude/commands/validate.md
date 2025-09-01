# Validate Code Against Organizational Standards

This command runs EgoKit policy validation to ensure code stays on-track with established patterns.

## Usage
- `/validate` - Validate changed files
- `/validate --all` - Validate entire codebase
- `/validate path/to/file.py` - Validate specific file

## Active Policy Rules
Currently enforcing 4 organizational standards:

### Critical Standards (Will Block Commits)

- **SEC-001**: Never commit credentials or secrets
- **DOCS-001**: Technical documentation must avoid superlatives and marketing language

## Implementation
```bash
# Run EgoKit validation
ego validate --changed --format json

# Parse results and provide summary
if [ $? -eq 0 ]; then
    echo "✅ All policy checks passed"
else
    echo "❌ Policy violations detected. Run 'ego validate --changed' for details."
fi
```

## Context
This command integrates with the organizational policy framework to prevent quality drift and ensure consistent agent behavior across all development activities.