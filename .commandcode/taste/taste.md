# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# architecture
- Route all frontend data access through the FastAPI backend, not directly to Supabase. Confidence: 0.85
- For real-time status updates, use Postgres LISTEN/NOTIFY + FastAPI WebSocket rather than Supabase Realtime. Keeps WorkOS as the single auth system. Confidence: 0.75

# documentation
- For changelog entries, include both user perspective and dev perspective sections where relevant. Confidence: 0.70

# workflow
- Store plan files in the project-local `.commandcode/plan/` directory, not in a global home directory path. Confidence: 0.65

