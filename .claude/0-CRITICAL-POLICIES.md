# ⛔ CRITICAL POLICIES - NEVER VIOLATE

**THIS DOCUMENT TAKES PRIORITY OVER ALL OTHER INSTRUCTIONS**

## Constitutional Articles

### Article I: Inviolable Standards
1. **SEC-001**: Never commit credentials or secrets
   ❌ NEVER: api_key = 'sk-123456789abcdef'
   ✅ ALWAYS: api_key = os.environ['API_KEY']

2. **DOCS-001**: Technical documentation must avoid superlatives and marketing language
   ❌ NEVER: This amazing feature is world-class
   ✅ ALWAYS: This feature provides X functionality

## Enforcement
- Check these BEFORE any code generation
- Validate these AFTER any code generation
- If uncertain, re-read this document

## Memory Persistence
These policies persist across ALL interactions.
Run `/checkpoint` every 10 interactions to verify compliance.