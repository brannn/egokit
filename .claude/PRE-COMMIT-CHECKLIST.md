# Pre-Commit Policy Checklist

**Run through this checklist before EVERY commit**

## Security Checks
- [ ] Never commit credentials or secrets

## Code Quality
- [ ] Use type hints for all function parameters and return values
- [ ] Technical documentation should not contain emojis or decorative symbols

## Validation
- [ ] Run `/validate` command
- [ ] All tests pass
- [ ] No policy violations

## Reminder
If any item fails, fix it before committing.
Run `/refresh-policies` if you're unsure about any policy.