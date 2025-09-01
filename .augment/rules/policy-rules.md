---
description: Security and quality policies that must be followed
type: always
---

# Policy Rules

## Critical Requirements

These rules must be followed and will block code if violated:

- Never commit credentials or secrets

```python
# Correct approach:
api_key = os.environ['API_KEY']
```

- Technical documentation must avoid superlatives and marketing language

```python
# Correct approach:
This feature provides X functionality
```

## Best Practices

Follow these guidelines for code quality:

- Use type hints for all function parameters and return values
- Technical documentation should not contain emojis or decorative symbols