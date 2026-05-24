# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# architecture
- Route all frontend data access through the FastAPI backend, not directly to Supabase. Confidence: 0.85
- When using WorkOS AuthKit with social providers (Google, etc.), sync real user profile data (email, name) from the identity provider to Supabase, not placeholder values. Confidence: 0.70
- For real-time status updates, use Postgres LISTEN/NOTIFY + FastAPI WebSocket rather than Supabase Realtime. Keeps WorkOS as the single auth system. Confidence: 0.75

# documentation
- For changelog entries, include both user perspective and dev perspective sections where relevant. Confidence: 0.70

# config
- Avoid `env_prefix` in pydantic-settings config.py — it applies to `.env` file entries too, silently ignoring unprefixed variables and falling back to defaults. Confidence: 0.70

# database
- During pre-production, consolidate all DB changes into the initial migration rather than creating multiple migrations. Use `supabase db push` for remote Supabase (not `supabase db reset` which is local-only). Confidence: 0.95

# workflow
- Store plan files in the project-local `.commandcode/plan/` directory, not in a global home directory path. Confidence: 0.65
- When debugging, trace existing code-level relationships to identify root causes rather than adding new code. Follow the breadcrumb trail from callers to callees. Confidence: 0.75
- After fixing one issue, continue investigating for other overlooked potential issues before declaring the problem solved. Confidence: 0.70
- When identifying code duplication, first determine if both instances are needed, then identify which pattern aligns with the codebase standard, then consolidate to that pattern before fixing the underlying issue. Confidence: 0.75
- Do not keep servers running after changes are made — the user prefers to manage their own server processes so they can restart when code changes. Kill servers instead of leaving them running. Confidence: 0.80

