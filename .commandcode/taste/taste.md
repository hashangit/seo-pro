# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# architecture
- Route all frontend data access through the FastAPI backend, not directly to Supabase. Confidence: 0.85
- When using WorkOS AuthKit with social providers (Google, etc.), sync real user profile data (email, name) from the identity provider to Supabase, not placeholder values. Confidence: 0.70
- For real-time status updates, use Postgres LISTEN/NOTIFY + FastAPI WebSocket rather than Supabase Realtime. Keeps WorkOS as the single auth system. Confidence: 0.75
- Individual analysis, page audit, and site audit should follow a unified flow: estimate credits → check user balance → deduct/request credits → run analysis → show results. Avoid diverging architectures for different analysis types. Confidence: 0.75

# documentation
- For changelog entries, include both user perspective and dev perspective sections where relevant. Confidence: 0.70

# config
- Avoid `env_prefix` in pydantic-settings config.py — it applies to `.env` file entries too, silently ignoring unprefixed variables and falling back to defaults. Confidence: 0.70

# database
- During pre-production, consolidate all DB changes into the initial migration rather than creating multiple migrations. Use `supabase db push` for remote Supabase (not `supabase db reset` which is local-only). Confidence: 0.95

# workflow
See [workflow/taste.md](workflow/taste.md)
