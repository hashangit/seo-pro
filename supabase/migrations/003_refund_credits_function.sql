-- Migration: Add refund_credits function
-- Version: 003
-- Description: Creates the refund_credits RPC function that was missing from the original schema
-- This fixes P0 issue: refund_credits is called in api/main.py but didn't exist

-- ============================================================================
-- Refund Credits Function (for task submission failures)
-- ============================================================================

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
    -- Validate inputs
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'user_id is required';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'amount must be a positive integer';
    END IF;

    -- Lock the row and get current balance
    SELECT credits_balance INTO v_current_balance
    FROM users
    WHERE id = p_user_id
    FOR UPDATE;

    -- Check user exists
    IF v_current_balance IS NULL THEN
        RAISE EXCEPTION 'User not found: %', p_user_id;
    END IF;

    -- Add credits back (refund)
    v_new_balance := v_current_balance + p_amount;
    UPDATE users
    SET credits_balance = v_new_balance,
        updated_at = NOW()
    WHERE id = p_user_id;

    -- Record refund transaction
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
        p_amount,
        v_new_balance,
        'refund',
        p_reference_id,
        p_reference_type,
        COALESCE(p_description, 'Credit refund')
    );

    RETURN jsonb_build_object(
        'success', true,
        'new_balance', v_new_balance,
        'refunded', p_amount,
        'previous_balance', v_current_balance
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION refund_credits TO authenticated, service_role;

-- Add comment for documentation
COMMENT ON FUNCTION refund_credits IS 'Refund credits to a user. Used when analysis fails after deduction. Atomic operation with row locking.';

-- ============================================================================
-- Also add missing transaction type 'refund' to constraint if not exists
-- ============================================================================

-- Check if 'refund' is already in the constraint
DO $$
BEGIN
    -- First check if the constraint exists and needs updating
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname LIKE '%credit_transactions_transaction_type%'
    ) THEN
        -- Drop and recreate constraint with 'refund' type included
        -- This is safe because we're adding a new valid value
        ALTER TABLE credit_transactions
        DROP CONSTRAINT IF EXISTS credit_transactions_transaction_type_check;

        ALTER TABLE credit_transactions
        ADD CONSTRAINT credit_transactions_transaction_type_check
        CHECK (transaction_type IN ('purchase', 'spend', 'refund', 'bonus'));
    END IF;
END $$;
