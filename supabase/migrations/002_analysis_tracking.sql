-- SEO Pro Analysis Tracking Migration
-- Schema version: 2.1.0
-- Adds tracking for individual analyses, page audits, and site audits

-- ============================================================================
-- Analyses table (tracks all analysis types)
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
    -- Add constraint: failed analyses must have error message
    CONSTRAINT analysis_failed_requires_error CHECK (
        status != 'failed' OR error_message IS NOT NULL
    ),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- Indexes for analyses table
-- ============================================================================

-- Composite index for user + status (dashboard queries)
CREATE INDEX IF NOT EXISTS idx_analyses_user_status ON analyses(user_id, status, created_at DESC);

-- Index for user + analysis_mode (filtering by mode)
CREATE INDEX IF NOT EXISTS idx_analyses_user_mode ON analyses(user_id, analysis_mode, created_at DESC);

-- Index for user + analysis_type (filtering by type)
CREATE INDEX IF NOT EXISTS idx_analyses_user_type ON analyses(user_id, analysis_type, created_at DESC);

-- Index for processing queries
CREATE INDEX IF NOT EXISTS idx_analyses_status_created ON analyses(status, created_at)
    WHERE status IN ('pending', 'processing');

-- ============================================================================
-- RLS Policies for analyses
-- ============================================================================

-- Enable RLS on analyses
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Users can view own analyses
CREATE POLICY "Users can view own analyses" ON analyses
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can manage analyses
CREATE POLICY "Service role can manage analyses" ON analyses
    FOR ALL TO service_role USING (true);

-- ============================================================================
-- Update credit_transactions reference_type constraint
-- ============================================================================

-- Drop the existing check constraint and add a new one that includes 'analysis'
ALTER TABLE credit_transactions
DROP CONSTRAINT IF EXISTS credit_transactions_reference_type_check;

-- Add new constraint with 'analysis' type
ALTER TABLE credit_transactions
ADD CONSTRAINT credit_transactions_reference_type_check
CHECK (reference_type IN ('audit', 'analysis', 'purchase', 'bonus', 'adjustment', 'refund', NULL::text));

-- ============================================================================
-- Grant Permissions
-- ============================================================================

GRANT SELECT ON analyses TO authenticated;
GRANT ALL ON analyses TO service_role;

-- ============================================================================
-- Helper function to create analysis record
-- ============================================================================

CREATE OR REPLACE FUNCTION create_analysis(
    p_user_id UUID,
    p_url TEXT,
    p_analysis_type VARCHAR(50),
    p_analysis_mode VARCHAR(20),
    p_credits_used INTEGER
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
        status
    ) VALUES (
        p_user_id,
        p_url,
        p_analysis_type,
        p_analysis_mode,
        p_credits_used,
        'processing'
    ) RETURNING id INTO v_analysis_id;

    RETURN v_analysis_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION create_analysis TO authenticated, service_role;

-- ============================================================================
-- Helper function to complete analysis
-- ============================================================================

CREATE OR REPLACE FUNCTION complete_analysis(
    p_analysis_id UUID,
    p_results JSONB
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE analyses
    SET status = 'completed',
        results_json = p_results,
        completed_at = NOW()
    WHERE id = p_analysis_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION complete_analysis TO authenticated, service_role;

-- ============================================================================
-- Helper function to fail analysis
-- ============================================================================

CREATE OR REPLACE FUNCTION fail_analysis(
    p_analysis_id UUID,
    p_error_message TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE analyses
    SET status = 'failed',
        error_message = p_error_message,
        completed_at = NOW()
    WHERE id = p_analysis_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION fail_analysis TO authenticated, service_role;

-- ============================================================================
-- Rollback documentation
-- ============================================================================
-- To rollback this migration:
-- DROP TABLE IF EXISTS analyses CASCADE;
-- DROP FUNCTION IF EXISTS create_analysis(), complete_analysis(), fail_analysis();
