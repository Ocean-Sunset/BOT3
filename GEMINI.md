# Project: Cipher Security Bot
## Core Principles
- **Zero Bloat:** If a feature doesn't protect the server or audit the API, it doesn't belong.
- **Performance:** Sub-100ms response time for moderation events.
- **Security:** No hardcoded secrets; strict OAuth2 verification.

## Architecture
- Use `discord.py` latest stable.
- Every command must have a 'Audit Log' entry requirement.
- The 'API Debugger' must be restricted to the Organization Owner only.