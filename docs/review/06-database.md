# 06 — Database

## Overview

The database is **Supabase PostgreSQL 17**, used exclusively as a data store — **not** for authentication (that's WorkOS). The schema is defined in a single migration file: `supabase/migrations/001_initial_schema.sql`.

## Schema: 7 Tables

### `organizations`
- Synced from WorkOS organization data
- Columns: `id` (UUID PK), `name`, `created_at`, `updated_at`

### `users`
- Synced from WorkOS user data on each authenticated request
- Columns: `id` (UUID PK), `email` (unique), `first_name`, `last_name`, `phone`, `address`, `city`, `organization_id` (FK → organizations), `credits_balance` (INT, ≥ 0), `created_at`, `updated_at`, `last_sync`

### `credit_transactions`
- Immutable ledger of all credit movements
- Columns: `id` (UUID PK), `user_id` (FK → users), `amount` (INT, negative=spend), `balance_after` (INT), `transaction_type` (purchase/spend/refund/bonus), `reference_id`, `reference_type` (audit/analysis/purchase/bonus/adjustment/refund), `description`, `created_at`

### `pending_audits`
- Quote management with 30-minute expiry
- Columns: `id` (UUID PK), `user_id` (FK → users), `url`, `page_count`, `credits_required`, `status` (pending/processing/approved/expired/cancelled), `created_at`, `expires_at` (NOW + 30min), `metadata` (JSONB)

### `audits`
- Full site audit records
- Columns: `id` (UUID PK), `user_id` (FK → users), `url`, `status` (queued/processing/completed/failed/cancelled), `page_count`, `credits_used`, `results_json` (JSONB), `error_message`, `created_at`, `completed_at`, `metadata` (JSONB)
- Constraint: `status='failed'` requires non-null `error_message`

### `audit_tasks`
- Subagent progress tracking for SDK worker
- Columns: `id` (UUID PK), `audit_id` (FK → audits), `task_type` (technical/content/schema/sitemap/performance/visual), `worker_type` (http/playwright/sdk), `status` (queued/processing/completed/failed), `result_json` (JSONB), `error_message`, `created_at`, `updated_at`, `completed_at`

### `analyses`
- Individual analysis tracking with status
- Columns: `id` (UUID PK), `user_id` (FK → users), `url`, `analysis_type` (12 types + page_audit + site_audit), `analysis_mode` (individual/page_audit/site_audit), `credits_used`, `status` (pending/processing/completed/failed/cancelled), `results_json` (JSONB), `error_message`, `created_at`, `updated_at`, `completed_at`, `metadata` (JSONB)
- Constraint: `status='failed'` requires non-null `error_message`

### `credit_requests`
- Manual payment flow tracking
- Columns: `id` (UUID PK), `user_id` (FK → users), `credits_requested`, `amount` (DECIMAL), `currency` (default USD), `status` (pending/invoice_sent/proof_uploaded/approved/rejected), `invoice_number` (unique), `invoice_url`, `payment_proof_url`, `payment_notes`, `admin_notes`, `reviewed_by` (FK → users), `reviewed_at`, `created_at`, `updated_at`

## Row-Level Security (RLS)

All 7 tables have RLS enabled with two levels:

1. **User policies**: Users can only see/update their own data:
   - `users`: `SELECT/USING (auth.uid() = id)`, `UPDATE/USING (auth.uid() = id)`
   - `credit_transactions`: `SELECT/USING (auth.uid() = user_id)`
   - `audits`: `SELECT/USING (auth.uid() = user_id)`
   - `analyses`: `SELECT/USING (auth.uid() = user_id)`
   - `credit_requests`: `SELECT/USING (auth.uid() = user_id)`, `INSERT/WITH CHECK (auth.uid() = user_id)`, `UPDATE/USING (auth.uid() = user_id)`
   - `audit_tasks`: `SELECT/USING (audit_id IN (SELECT id FROM audits WHERE user_id = auth.uid()))`

2. **Service role policies**: Full access to all tables for the backend:
   - All tables: `FOR ALL TO service_role USING (true)`

## Atomic Credit Functions

Three critical PostgreSQL functions using `FOR UPDATE` row locks to prevent race conditions:

### `deduct_credits(p_user_id, p_amount, p_reference_id, p_reference_type, p_description)`
```
1. SELECT credits_balance FOR UPDATE (row lock)
2. Check sufficient balance → RAISE EXCEPTION if insufficient
3. UPDATE users SET credits_balance = new_balance
4. INSERT INTO credit_transactions (spend, negative amount)
5. RETURN jsonb(success, new_balance, deducted)
```

### `add_credits(p_user_id, p_amount, p_description)`
```
1. SELECT credits_balance FOR UPDATE (row lock)
2. UPDATE users SET credits_balance = new_balance
3. INSERT INTO credit_transactions (purchase, positive amount)
4. RETURN jsonb(success, new_balance, added)
```

### `refund_credits(p_user_id, p_amount, p_reference_id, p_reference_type, p_description)`
```
1. Validate inputs (non-null, positive)
2. SELECT credits_balance FOR UPDATE (row lock)
3. UPDATE users SET credits_balance = new_balance
4. INSERT INTO credit_transactions (refund, positive amount)
5. RETURN jsonb(success, new_balance, refunded, previous_balance)
```

All three are `SECURITY DEFINER` with `GRANT EXECUTE TO authenticated, service_role`.

## Analysis Record Functions

### `create_analysis_record(p_user_id, p_url, p_analysis_type, p_analysis_mode, p_credits_used, p_status, p_results_json, p_error_message)`
Inserts into `analyses` table and returns the new UUID.

### `update_analysis_record(p_analysis_id, p_status, p_results_json, p_error_message)`
Updates analysis status and optionally sets `completed_at` timestamp.

## Cleanup Functions

### `cleanup_expired_quotes()`
Deletes expired pending_audits (status=pending, expires_at < NOW) → returns count.

### `cleanup_expired_quotes_with_stats()`
Same but returns JSONB with `{success, deleted_count, cleaned_at}`.

## Triggers

Auto-update `updated_at` on modification for: `organizations`, `users`, `credit_requests`, `audit_tasks`, `analyses`.

## Indexes

Key indexes for performance:
- `users`: `credits_balance`, `organization_id`
- `credit_transactions`: `(user_id, created_at DESC)`, `(user_id, created_at DESC) WHERE type IN ('purchase','spend')`
- `pending_audits`: `(user_id, created_at DESC)`, `(status, expires_at) WHERE status='pending'`
- `audits`: `(user_id, status, created_at DESC)`
- `audit_tasks`: `audit_id`, `(status, created_at) WHERE status IN ('queued','processing')`
- `analyses`: `(user_id, status, created_at DESC)`, `(user_id, analysis_mode, created_at DESC)`, `(user_id, analysis_type, created_at DESC)`, `(status, created_at) WHERE status IN ('pending','processing')`
- `credit_requests`: `(user_id, created_at DESC)`, `(status, created_at DESC) WHERE status IN ('pending','proof_uploaded')`

## Supabase Local Dev Config

From `supabase/config.toml`:
- Project: `taipei-v1`
- PostgreSQL 17
- Ports: API 54321, DB 54322, Studio 54323, Inbucket 54324
- Auth: disabled locally (WorkOS handles production auth)
- RLS: enabled
- Real-time: enabled
- Storage: enabled (50Mi limit)
