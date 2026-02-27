-- SEO Pro Database Schema
-- Schema version: 1.0.0
-- Credit-based topup model with audit tracking

-- Enable required extensions
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_credits_balance ON users(credits_balance);
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);

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
    reference_type VARCHAR(50) CHECK (reference_type IN ('audit', 'analysis', 'purchase', 'bonus', 'adjustment', 'refund', NULL)),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_balance ON credit_transactions(user_id, created_at DESC)
    WHERE transaction_type IN ('purchase', 'spend');

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

CREATE INDEX IF NOT EXISTS idx_pending_audits_user_id ON pending_audits(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pending_audits_status_expires ON pending_audits(status, expires_at)
    WHERE status = 'pending';

-- ============================================================================
-- Audit jobs (full site audits)
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
    CONSTRAINT audit_failed_requires_error CHECK (
        status != 'failed' OR error_message IS NOT NULL
    ),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audits_user_status ON audits(user_id, status, created_at DESC);

-- ============================================================================
-- Audit tasks (subagent tracking for SDK worker)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('technical', 'content', 'schema', 'sitemap', 'performance', 'visual')),
    worker_type VARCHAR(50) NOT NULL CHECK (worker_type IN ('http', 'playwright', 'sdk')),
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    result_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_audit_tasks_audit_id ON audit_tasks(audit_id);
CREATE INDEX IF NOT EXISTS idx_audit_tasks_status_created ON audit_tasks(status, created_at)
    WHERE status IN ('queued', 'processing');

-- ============================================================================
-- Analyses (individual analysis tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    analysis_type VARCHAR(50) NOT NULL
        CHECK (analysis_type IN ('technical', 'content', 'schema', 'geo', 'sitemap', 'hreflang', 'images', 'visual', 'performance', 'plan', 'programmatic', 'competitor-pages', 'page_audit', 'site_audit')),
    analysis_mode VARCHAR(20) NOT NULL
        CHECK (analysis_mode IN ('individual', 'page_audit', 'site_audit')),
    credits_used INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    results_json JSONB,
    error_message TEXT,
    CONSTRAINT analysis_failed_requires_error CHECK (
        status != 'failed' OR error_message IS NOT NULL
    ),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_analyses_user_status ON analyses(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_user_mode ON analyses(user_id, analysis_mode, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_user_type ON analyses(user_id, analysis_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_status_created ON analyses(status, created_at)
    WHERE status IN ('pending', 'processing');

-- ============================================================================
-- Credit Requests (Manual Payment Flow)
-- ============================================================================

CREATE TABLE IF NOT EXISTS credit_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credits_requested INTEGER NOT NULL CHECK (credits_requested > 0),
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending'
        CHECK (status IN ('pending', 'invoice_sent', 'proof_uploaded', 'approved', 'rejected')),
    invoice_number VARCHAR(50) UNIQUE,
    invoice_url TEXT,
    payment_proof_url TEXT,
    payment_notes TEXT,
    admin_notes TEXT,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_requests_user_id ON credit_requests(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_requests_status ON credit_requests(status, created_at DESC)
    WHERE status IN ('pending', 'proof_uploaded');

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_requests ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view own data" ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Service role can manage users" ON users FOR ALL TO service_role USING (true);

-- Organizations policies
CREATE POLICY "Users can view own organization" ON organizations FOR SELECT USING (
    id IN (SELECT organization_id FROM users WHERE id = auth.uid())
);
CREATE POLICY "Service role can manage organizations" ON organizations FOR ALL TO service_role USING (true);

-- Credit transactions policies
CREATE POLICY "Users can view own transactions" ON credit_transactions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage transactions" ON credit_transactions FOR ALL TO service_role USING (true);

-- Pending audits policies
CREATE POLICY "Users can view own pending audits" ON pending_audits FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage pending audits" ON pending_audits FOR ALL TO service_role USING (true);

-- Audits policies
CREATE POLICY "Users can view own audits" ON audits FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage audits" ON audits FOR ALL TO service_role USING (true);

-- Audit tasks policies
CREATE POLICY "Users can view own audit tasks" ON audit_tasks FOR SELECT USING (
    audit_id IN (SELECT id FROM audits WHERE user_id = auth.uid())
);
CREATE POLICY "Service role can manage audit tasks" ON audit_tasks FOR ALL TO service_role USING (true);

-- Analyses policies
CREATE POLICY "Users can view own analyses" ON analyses FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage analyses" ON analyses FOR ALL TO service_role USING (true);

-- Credit requests policies
CREATE POLICY "Users can view own credit requests" ON credit_requests FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create credit requests" ON credit_requests FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own credit requests" ON credit_requests FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage credit requests" ON credit_requests FOR ALL TO service_role USING (true);

-- ============================================================================
-- Helper Functions
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Updated_at Triggers
-- ============================================================================

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_credit_requests_updated_at BEFORE UPDATE ON credit_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audit_tasks_updated_at BEFORE UPDATE ON audit_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analyses_updated_at BEFORE UPDATE ON analyses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Atomic Credit Functions
-- ============================================================================

-- Deduct credits atomically
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
BEGIN
    SELECT credits_balance INTO v_current_balance
    FROM users WHERE id = p_user_id FOR UPDATE;

    IF v_current_balance IS NULL THEN
        RAISE EXCEPTION 'User not found: %', p_user_id;
    END IF;

    IF v_current_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient credits: balance=%, required=%',
            v_current_balance, p_amount USING ERRCODE = 'INSUFFICIENT_FUNDS';
    END IF;

    v_new_balance := v_current_balance - p_amount;
    UPDATE users SET credits_balance = v_new_balance, updated_at = NOW() WHERE id = p_user_id;

    INSERT INTO credit_transactions (user_id, amount, balance_after, transaction_type, reference_id, reference_type, description)
    VALUES (p_user_id, -p_amount, v_new_balance, 'spend', p_reference_id, p_reference_type, p_description);

    RETURN jsonb_build_object('success', true, 'new_balance', v_new_balance, 'deducted', p_amount);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add credits
CREATE OR REPLACE FUNCTION add_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_description TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
BEGIN
    SELECT credits_balance INTO v_current_balance
    FROM users WHERE id = p_user_id FOR UPDATE;

    IF v_current_balance IS NULL THEN
        RAISE EXCEPTION 'User not found: %', p_user_id;
    END IF;

    v_new_balance := v_current_balance + p_amount;
    UPDATE users SET credits_balance = v_new_balance, updated_at = NOW() WHERE id = p_user_id;

    INSERT INTO credit_transactions (user_id, amount, balance_after, transaction_type, description)
    VALUES (p_user_id, p_amount, v_new_balance, 'purchase', p_description);

    RETURN jsonb_build_object('success', true, 'new_balance', v_new_balance, 'added', p_amount);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Refund credits
CREATE OR REPLACE FUNCTION refund_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_reference_id UUID DEFAULT NULL,
    p_reference_type VARCHAR(50) DEFAULT NULL,
    p_description TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'user_id is required';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'amount must be a positive integer';
    END IF;

    SELECT credits_balance INTO v_current_balance
    FROM users WHERE id = p_user_id FOR UPDATE;

    IF v_current_balance IS NULL THEN
        RAISE EXCEPTION 'User not found: %', p_user_id;
    END IF;

    v_new_balance := v_current_balance + p_amount;
    UPDATE users SET credits_balance = v_new_balance, updated_at = NOW() WHERE id = p_user_id;

    INSERT INTO credit_transactions (user_id, amount, balance_after, transaction_type, reference_id, reference_type, description)
    VALUES (p_user_id, p_amount, v_new_balance, 'refund', p_reference_id, p_reference_type, COALESCE(p_description, 'Credit refund'));

    RETURN jsonb_build_object('success', true, 'new_balance', v_new_balance, 'refunded', p_amount, 'previous_balance', v_current_balance);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION deduct_credits TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION add_credits TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION refund_credits TO authenticated, service_role;

-- ============================================================================
-- Analysis Record Functions
-- ============================================================================

-- Create analysis record
CREATE OR REPLACE FUNCTION create_analysis_record(
    p_user_id UUID,
    p_url TEXT,
    p_analysis_type VARCHAR(50),
    p_analysis_mode VARCHAR(20),
    p_credits_used INTEGER,
    p_status VARCHAR(50) DEFAULT 'pending',
    p_results_json JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_analysis_id UUID;
BEGIN
    INSERT INTO analyses (
        user_id,
        url,
        analysis_type,
        analysis_mode,
        credits_used,
        status,
        results_json,
        error_message
    ) VALUES (
        p_user_id,
        p_url,
        p_analysis_type,
        p_analysis_mode,
        p_credits_used,
        p_status,
        p_results_json,
        p_error_message
    ) RETURNING id INTO v_analysis_id;

    RETURN v_analysis_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION create_analysis_record TO authenticated, service_role;

-- Update analysis record
CREATE OR REPLACE FUNCTION update_analysis_record(
    p_analysis_id UUID,
    p_status VARCHAR(50),
    p_results_json JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE analyses SET
        status = p_status,
        results_json = COALESCE(p_results_json, results_json),
        error_message = COALESCE(p_error_message, error_message),
        completed_at = CASE WHEN p_status IN ('completed', 'failed') THEN NOW() ELSE completed_at END,
        updated_at = NOW()
    WHERE id = p_analysis_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION update_analysis_record TO authenticated, service_role;

-- ============================================================================
-- Cleanup Functions
-- ============================================================================

-- Clean up expired pending_audits (returns count only)
CREATE OR REPLACE FUNCTION cleanup_expired_quotes()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM pending_audits
    WHERE expires_at < NOW()
    AND status = 'pending';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION cleanup_expired_quotes TO authenticated, service_role;

-- Clean up expired pending_audits (returns stats as JSONB)
CREATE OR REPLACE FUNCTION cleanup_expired_quotes_with_stats()
RETURNS JSONB AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM pending_audits
    WHERE expires_at < NOW()
    AND status = 'pending';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN jsonb_build_object(
        'success', true,
        'deleted_count', deleted_count,
        'cleaned_at', NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION cleanup_expired_quotes_with_stats TO service_role;

-- ============================================================================
-- Grant Permissions
-- ============================================================================

GRANT USAGE ON SCHEMA public TO postgres, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO anon;
