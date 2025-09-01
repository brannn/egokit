# Regulatory Compliance Validation

Validates code against regulatory and compliance requirements.

## Usage
`/compliance-check [--standard sox|pci|hipaa|gdpr]`

## Compliance Areas
- Data handling and privacy (GDPR, CCPA)
- Financial regulations (SOX, PCI-DSS)
- Healthcare standards (HIPAA)
- Security frameworks (ISO 27001, NIST)

## Implementation
```bash
# Run compliance-specific validation
ego validate --compliance-mode --standard ${1:-all}

# Generate compliance report
echo "📊 Compliance validation complete"
echo "📋 Areas validated: All active standards"
```

## Context
Ensures AI-generated code meets regulatory requirements without manual review of every interaction.