# Switch to Security Review Mode

Activates heightened security analysis with threat modeling focus.

## Usage
`/security-review`

## Behavior Changes
- Enhanced security vulnerability detection
- Threat modeling considerations for all code changes
- OWASP Top 10 validation
- Cryptographic implementation review
- Authentication and authorization analysis

## Active Security Policies

- **SEC-001**: Never commit credentials or secrets

## Implementation
```bash
export EGOKIT_MODE="security"
echo "🔒 Security review mode activated. All code will be analyzed for security implications."
```

## Context
This mode calibrates agent behavior for security-focused analysis, ensuring consistent application of security standards and threat awareness.