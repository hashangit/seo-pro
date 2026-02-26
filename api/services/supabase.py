"""
Supabase Client Service

Singleton Supabase client for database operations.
"""

from typing import Optional

# Global client instance
_supabase_client: Optional[object] = None


def get_supabase_client():
    """Get Supabase client singleton for database operations."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        from config import get_settings
        settings = get_settings()
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _supabase_client


def reset_supabase_client():
    """Reset the Supabase client (used for testing or reconnection)."""
    global _supabase_client
    _supabase_client = None
