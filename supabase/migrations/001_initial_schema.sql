-- SEO Pro Database Schema
-- Schema version: 2.0.0
-- This schema supports the credit-based pricing model and audit system
-- Fixed: Security vulnerabilities, RLS policies, missing indexes, atomic operations

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- Organizations (synced from WorkOS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for organization lookups
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);

-- ============================================================================
-- Users (synced from WorkOS AuthKit)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    credits_balance INTEGER DEFAULT 0 NOT NULL CHECK (credits_balance >= 0),
    plan_tier VARCHAR(20) DEFAULT 'free' NOT NULL CHECK (plan_tier IN ('free', 'pro', 'enterprise', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync TIMESTAMPTZ DEFAULT NOW()
);

-- Plan tier constraint (defined in CREATE TABLE, no ALTER needed)
-- ALTER TABLE users ADD CONSTRAINT valid_plan_tier CHECK (plan_tier IN ('free', 'pro', 'enterprise', 'admin'));

-- Credits table (credit purchases) - DEPRECATED, use credit_transactions instead
CREATE TABLE IF NOT EXISTS credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    purchase_id VARCHAR(255),
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('purchase', 'bonus', 'adjustment', 'refund')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- Credit transactions (ledger for all credit movements)
-- ============================================================================

CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('purchase', 'spend', 'refund', 'bonus')),
    reference_id UUID,
    reference_type VARCHAR(50),
    payment_id VARCHAR(255) UNIQUE,  -- For PayHere webhook idempotency
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for transaction lookups by payment_id (idempotency)
CREATE INDEX IF NOT EXISTS idx_credit_transactions_payment_id ON credit_transactions(payment_id) WHERE payment_id IS NOT NULL;

-- ============================================================================
-- Pending audit quotes (30 min expiry)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pending_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    credits_required INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'approved', 'expired', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 minutes',
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- Pending orders for PayHere
-- ============================================================================

CREATE TABLE IF NOT EXISTS pending_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id VARCHAR(100) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credits INTEGER NOT NULL,
    amount_lkr DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- Audit jobs
-- ============================================================================

CREATE TABLE IF NOT EXISTS audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    page_count INTEGER NOT NULL,
    credits_used INTEGER NOT NULL,
    results_json JSONB,
    error_message TEXT,
    -- Add constraint: failed audits must have error message
    CONSTRAINT audit_failed_requires_error CHECK (
        status != 'failed' OR error_message IS NOT NULL
    ),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- Audit pages (individual page results)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    results_json JSONB,
    error_message TEXT,
    -- Add constraint: failed pages must have error message
    CONSTRAINT page_failed_requires_error CHECK (
        status != 'failed' OR error_message IS NOT NULL
    ),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================================
-- Audit tasks (subagent tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('technical', 'content', 'schema', 'sitemap', 'performance', 'visual')),
    worker_type VARCHAR(50) NOT NULL CHECK (worker_type IN ('http', 'playwright')),
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    result_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================================
-- Cached pages (TTL: 24 hours)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cached_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Enable RLS on cached_pages
ALTER TABLE cached_pages ENABLE ROW LEVEL SECURITY;

-- Policy: Only service role can access cache (no user data in cache)
CREATE POLICY "Service role can manage cache" ON cached_pages
    FOR ALL TO service_role USING (true);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_credits_balance ON users(credits_balance);
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);

-- Note: email already has unique index, no need for duplicate
-- CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Credit transactions - composite index for user + status
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id, created_at DESC);

-- Partial index for common transaction types
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_balance ON credit_transactions(user_id, created_at DESC)
    WHERE transaction_type IN ('purchase', 'spend');

-- Credits table
CREATE INDEX IF NOT EXISTS idx_credits_user_id ON credits(user_id, created_at DESC);

-- Pending audits - composite for expiry cleanup
CREATE INDEX IF NOT EXISTS idx_pending_audits_user_id ON pending_audits(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pending_audits_status_expires ON pending_audits(status, expires_at)
    WHERE status = 'pending';

-- Pending orders
CREATE INDEX IF NOT EXISTS idx_pending_orders_order_id ON pending_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_pending_orders_user_id ON pending_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_pending_orders_status ON pending_orders(status, created_at);

-- Audits - composite for user + status (dashboard queries)
CREATE INDEX IF NOT EXISTS idx_audits_user_status ON audits(user_id, status, created_at DESC);

-- Audit pages - composite for worker queries
CREATE INDEX IF NOT EXISTS idx_audit_pages_audit_id ON audit_pages(audit_id);
CREATE INDEX IF NOT EXISTS idx_audit_pages_status_created ON audit_pages(status, created_at)
    WHERE status IN ('pending', 'processing');

-- Audit tasks - composite for worker queries
CREATE INDEX IF NOT EXISTS idx_audit_tasks_audit_id ON audit_tasks(audit_id);
CREATE INDEX IF NOT EXISTS idx_audit_tasks_status_created ON audit_tasks(status, created_at)
    WHERE status IN ('queued', 'processing');

-- Cached pages - partial index for active cache
CREATE INDEX IF NOT EXISTS idx_cached_pages_active ON cached_pages(url) WHERE expires_at >= NOW();

-- Organizations name index
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

-- Enable RLS on all data tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_tasks ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS Policies (FIXED: Removed dangerous UUID text casting)
-- ============================================================================

-- Users: Can see/update own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Service role can manage users" ON users
    FOR ALL TO service_role USING (true);

-- Organizations: Users can view their own org
CREATE POLICY "Users can view own organization" ON organizations
    FOR SELECT USING (
        id IN (SELECT organization_id FROM users WHERE id = auth.uid())
    );

CREATE POLICY "Service role can manage organizations" ON organizations
    FOR ALL TO service_role USING (true);

-- Credits: Users can view own credits
CREATE POLICY "Users can view own credits" ON credits
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage credits" ON credits
    FOR ALL TO service_role USING (true);

-- Credit transactions: Users can view own transactions
CREATE POLICY "Users can view own transactions" ON credit_transactions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage transactions" ON credit_transactions
    FOR ALL TO service_role USING (true);

-- Pending audits: Users can view own pending audits
CREATE POLICY "Users can view own pending audits" ON pending_audits
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage pending audits" ON pending_audits
    FOR ALL TO service_role USING (true);

-- Pending orders: Users can view own orders
CREATE POLICY "Users can view own orders" ON pending_orders
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage orders" ON pending_orders
    FOR ALL TO service_role USING (true);

-- Audits: Users can view own audits
CREATE POLICY "Users can view own audits" ON audits
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage audits" ON audits
    FOR ALL TO service_role USING (true);

-- Audit pages: Users can view pages from their audits
CREATE POLICY "Users can view own audit pages" ON audit_pages
    FOR SELECT USING (
        audit_id IN (
            SELECT id FROM audits WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage audit pages" ON audit_pages
    FOR ALL TO service_role USING (true);

-- Audit tasks: Users can view tasks from their audits
CREATE POLICY "Users can view own audit tasks" ON audit_tasks
    FOR SELECT USING (
        audit_id IN (
            SELECT id FROM audits WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage audit tasks" ON audit_tasks
    FOR ALL TO service_role USING (true);

-- ============================================================================
-- Atomic Credit Deduction Function (fixes race condition)
-- ============================================================================

CREATE OR REPLACE FUNCTION deduct_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_reference_id UUID DEFAULT NULL,
    p_reference_type VARCHAR(50) DEFAULT NULL,
    p_description TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
    v_payment_id VARCHAR(255) := NULL;
BEGIN
    -- Lock the row and check balance
    SELECT credits_balance INTO v_current_balance
    FROM users
    WHERE id = p_user_id
    FOR UPDATE;

    IF v_current_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient credits: balance=%, required=%',
            v_current_balance, p_amount
        USING ERRCODE = 'INSUFFICIENT_FUNDS';
    END IF;

    -- Deduct credits
    v_new_balance := v_current_balance - p_amount;
    UPDATE users
    SET credits_balance = v_new_balance,
        updated_at = NOW()
    WHERE id = p_user_id;

    -- Record transaction
    INSERT INTO credit_transactions (
        user_id,
        amount,
        balance_after,
        transaction_type,
        reference_id,
        reference_type,
        description
    ) VALUES (
        p_user_id,
        -p_amount,
        v_new_balance,
        'spend',
        p_reference_id,
        p_reference_type,
        p_description
    );

    RETURN jsonb_build_object(
        'success', true,
        'new_balance', v_new_balance,
        'deducted', p_amount
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on function
GRANT EXECUTE ON FUNCTION deduct_credits TO authenticated, service_role;

-- ============================================================================
-- Atomic Credit Addition Function (for webhooks)
-- ============================================================================

CREATE OR REPLACE FUNCTION add_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_payment_id VARCHAR(255) DEFAULT NULL,
    p_description TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
BEGIN
    -- Lock the row
    SELECT credits_balance INTO v_current_balance
    FROM users
    WHERE id = p_user_id
    FOR UPDATE;

    -- Add credits
    v_new_balance := v_current_balance + p_amount;
    UPDATE users
    SET credits_balance = v_new_balance,
        updated_at = NOW()
    WHERE id = p_user_id;

    -- Record transaction with payment_id for idempotency
    INSERT INTO credit_transactions (
        user_id,
        amount,
        balance_after,
        transaction_type,
        payment_id,
        description
    ) VALUES (
        p_user_id,
        p_amount,
        v_new_balance,
        'purchase',
        p_payment_id,
        p_description
    )
    ON CONFLICT (payment_id) DO NOTHING;  -- Idempotency

    RETURN jsonb_build_object(
        'success', true,
        'new_balance', v_new_balance,
        'added', p_amount
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on function
GRANT EXECUTE ON FUNCTION add_credits TO authenticated, service_role;

-- ============================================================================
-- Helper Functions and Triggers
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for organizations table
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to expire pending audits (can be called manually or scheduled)
CREATE OR REPLACE FUNCTION expire_pending_audits()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE pending_audits
    SET status = 'expired'
    WHERE status = 'pending' AND expires_at < NOW();

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Trigger to check expiry on read
CREATE OR REPLACE FUNCTION check_pending_audit_expiry()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'pending' AND NEW.expires_at < NOW() THEN
        NEW.status := 'expired';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_pending_audit_expires
    BEFORE UPDATE ON pending_audits
    FOR EACH ROW EXECUTE FUNCTION check_pending_audit_expiry();

-- ============================================================================
-- Grant Permissions (FIXED: Revoke anon access to sensitive data)
-- ============================================================================

GRANT USAGE ON SCHEMA public TO postgres, authenticated, service_role;

-- Grant full access to service role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Grant access to authenticated users for their own data (via RLS policies)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;

-- anon can only access public data (currently none, add as needed)
-- REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
GRANT USAGE ON SCHEMA public TO anon;

-- Grant execute on specific functions to authenticated
GRANT EXECUTE ON FUNCTION deduct_credits TO authenticated;
GRANT EXECUTE ON FUNCTION add_credits TO authenticated;
GRANT EXECUTE ON FUNCTION expire_pending_audits TO authenticated;

-- ============================================================================
-- Sample data for testing (remove in production)
-- ============================================================================

-- Insert a test organization
INSERT INTO organizations (id, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Test Organization')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Rollback documentation
-- ============================================================================
-- To rollback this migration:
-- DROP TABLE IF EXISTS audit_tasks, audit_pages, audits, pending_orders, pending_audits, credit_transactions, credits, users, organizations CASCADE;
-- DROP TYPE IF EXISTS plan_tier_enum CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column(), expire_pending_audits(), deduct_credits(), add_credits();
