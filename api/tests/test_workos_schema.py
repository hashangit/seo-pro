"""
Schema regression tests for WorkOS AuthKit identifiers.
"""

from pathlib import Path


SCHEMA = Path("supabase/migrations/001_initial_schema.sql").read_text()


def test_workos_synced_identity_columns_are_text():
    """WorkOS IDs are string IDs like user_... and org_..., not UUIDs."""
    assert "CREATE TABLE IF NOT EXISTS organizations (\n    id TEXT PRIMARY KEY" in SCHEMA
    assert "CREATE TABLE IF NOT EXISTS users (\n    id TEXT PRIMARY KEY" in SCHEMA
    assert "organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL" in SCHEMA


def test_workos_user_foreign_keys_and_credit_functions_accept_text_ids():
    """Every FK/function boundary that receives a WorkOS user id must accept text."""
    assert "user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE" in SCHEMA
    assert "reviewed_by TEXT REFERENCES users(id)" in SCHEMA
    assert "p_user_id TEXT" in SCHEMA


def test_rls_policies_compare_against_jwt_subject():
    """RLS policies should compare text WorkOS subjects, not Supabase UUID auth.uid()."""
    assert "(auth.jwt() ->> 'sub') = id" in SCHEMA
    assert "(auth.jwt() ->> 'sub') = user_id" in SCHEMA
