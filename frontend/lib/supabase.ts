/**
 * Supabase Client Configuration
 *
 * This client is used for data operations only.
 * Authentication is handled by WorkOS AuthKit.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!;

export const supabase = createClient(supabaseUrl, supabasePublishableKey);

/**
 * Database types
 */
export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  address: string | null;
  city: string | null;
  organization_id: string | null;
  credits_balance: number;
  created_at: string;
  updated_at: string;
  last_sync: string;
}

export interface CreditTransaction {
  id: string;
  user_id: string;
  amount: number;
  balance_after: number;
  transaction_type: "purchase" | "spend" | "refund" | "bonus";
  reference_id: string | null;
  reference_type: string | null;
  description: string | null;
  created_at: string;
}

export interface Audit {
  id: string;
  user_id: string;
  url: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  page_count: number;
  credits_used: number;
  results_json: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PendingAudit {
  id: string;
  user_id: string;
  url: string;
  page_count: number;
  credits_required: number;
  status: "pending" | "approved" | "expired" | "cancelled";
  created_at: string;
  expires_at: string;
  metadata: Record<string, unknown>;
}
