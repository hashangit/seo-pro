/**
 * API Client for SEO Pro Backend
 *
 * Handles all communication with the FastAPI backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

/**
 * Custom error class for authentication errors
 */
export class AuthError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = "AuthError";
  }
}

/**
 * Get auth token from WorkOS AuthKit
 *
 * WorkOS AuthKit stores the access token in memory and manages it.
 * The SDK automatically handles token refresh when tokens expire.
 *
 * @returns The access token or null if not authenticated
 * @throws {AuthError} If there's an error retrieving the token
 */
async function getAuthToken(): Promise<string | null> {
  if (typeof document === "undefined") return null;

  let retries = 0;
  const maxRetries = 2;

  while (retries <= maxRetries) {
    try {
      // Dynamic import to avoid SSR issues
      const { getAccessToken } = await import("@workos-inc/authkit-react");
      const token = await getAccessToken();

      if (!token) {
        // User is not authenticated
        return null;
      }

      return token;
    } catch (error) {
      retries++;

      // Check if this is a retriable error
      const isRetriable = error instanceof TypeError ||
                         (error instanceof Error && error.message.includes("fetch"));

      if (retries <= maxRetries && isRetriable) {
        // Wait a bit before retrying (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 100 * retries));
        continue;
      }

      // Log the error for debugging
      console.error("Failed to get WorkOS token:", error);

      // Throw a more specific error that can be caught and handled by the UI
      throw new AuthError(
        "Unable to authenticate. Please sign in again.",
        "AUTH_TOKEN_ERROR"
      );
    }
  }

  return null;
}

/**
 * Get the current authenticated user from WorkOS
 *
 * @returns The user object or null if not authenticated
 */
export async function getCurrentUser() {
  if (typeof document === "undefined") return null;

  try {
    const { getUser } = await import("@workos-inc/authkit-react");
    const user = await getUser();
    return user;
  } catch (error) {
    console.error("Failed to get user:", error);
    return null;
  }
}

/**
 * Sign out the current user
 */
export async function signOut() {
  if (typeof document === "undefined") return;

  try {
    const { signOut: workOSSignOut } = await import("@workos-inc/authkit-react");
    await workOSSignOut();
  } catch (error) {
    console.error("Failed to sign out:", error);
  }
}

/**
 * Make authenticated API request
 *
 * @throws {AuthError} If authentication fails (401/403 responses)
 * @throws {Error} For other API errors
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken();
  const url = `${API_URL}${endpoint}`;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle authentication errors specifically
  if (response.status === 401) {
    throw new AuthError(
      "Your session has expired. Please sign in again.",
      "SESSION_EXPIRED"
    );
  }

  if (response.status === 403) {
    throw new AuthError(
      "You don't have permission to access this resource.",
      "FORBIDDEN"
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    const errorMessage = error.detail || error.message || "API request failed";
    throw new Error(errorMessage);
  }

  return response.json();
}

// ============================================================================
// Credits API
// ============================================================================

export interface CreditBalanceResponse {
  balance: number;
  formatted: string;
}

export async function getCreditBalance(): Promise<CreditBalanceResponse> {
  return apiRequest<CreditBalanceResponse>("/api/v1/credits/balance");
}

// NOTE: purchaseCredits function removed pending IPG integration
// TODO: Implement payment flow when IPG is integrated

// ============================================================================
// Audit API
// ============================================================================

export interface AuditEstimateRequest {
  url: string;
  max_pages?: number;
}

export interface AuditEstimateResponse {
  url: string;
  estimated_pages: number;
  credits_required: number;
  cost_lkr: number;
  cost_usd: number;
  breakdown: string;
  quote_id: string;
  expires_at: string;
}

export async function estimateAudit(
  request: AuditEstimateRequest
): Promise<AuditEstimateResponse> {
  return apiRequest<AuditEstimateResponse>("/api/v1/audit/estimate", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export interface AuditRunRequest {
  quote_id: string;
}

export interface AuditRunResponse {
  audit_id: string;
  status: string;
}

export async function runAudit(
  quote_id: string
): Promise<AuditRunResponse> {
  return apiRequest<AuditRunResponse>("/api/v1/audit/run", {
    method: "POST",
    body: JSON.stringify({ quote_id }),
  });
}

export interface AuditStatusResponse {
  id: string;
  url: string;
  status: string;
  page_count: number;
  credits_used: number;
  created_at: string;
  completed_at: string | null;
  results: Record<string, unknown> | null;
  error_message: string | null;
}

export async function getAuditStatus(
  audit_id: string
): Promise<AuditStatusResponse> {
  return apiRequest<AuditStatusResponse>(`/api/v1/audit/${audit_id}`);
}

export interface AuditListResponse {
  audits: AuditStatusResponse[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export async function listAudits(
  limit: number = 100,
  offset: number = 0
): Promise<AuditListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString()
  });
  return apiRequest<AuditListResponse>(`/api/v1/audit?${params}`);
}

// ============================================================================
// Credit History Types
// ============================================================================

export interface CreditTransaction {
  id: string;
  user_id: string;
  amount: number;
  balance_after: number;
  transaction_type: "purchase" | "spend" | "refund" | "bonus";
  reference_id: string | null;
  reference_type: string | null;
  payment_id: string | null;
  description: string | null;
  created_at: string;
}

export interface CreditHistoryResponse {
  transactions: CreditTransaction[];
  total_purchased: number;
  total_spent: number;
}

export async function getCreditHistory(): Promise<CreditHistoryResponse> {
  return apiRequest<CreditHistoryResponse>("/api/v1/credits/history");
}
