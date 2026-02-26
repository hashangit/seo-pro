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

// ============================================================================
// Individual Analysis API
// ============================================================================

export interface AnalyzeRequest {
  url: string;
}

export interface AnalyzeResponse {
  category: string;
  score?: number;
  issues: Array<{ check: string; status: string; value?: string }>;
  warnings: Array<{ check: string; status: string; value?: string }>;
  passes: Array<{ check: string; status: string; value?: string }>;
  recommendations: string[];
  error?: string;
}

/**
 * Run technical SEO analysis
 */
export async function analyzeTechnical(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/technical", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run content quality (E-E-A-T) analysis
 */
export async function analyzeContent(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/content", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run schema markup analysis
 */
export async function analyzeSchema(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/schema", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run GEO (AI Search) optimization analysis
 */
export async function analyzeGeo(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/geo", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run sitemap analysis
 */
export async function analyzeSitemap(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/sitemap", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run hreflang/international SEO analysis
 */
export async function analyzeHreflang(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/hreflang", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run image SEO analysis
 */
export async function analyzeImages(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/images", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run visual SEO analysis (requires Browser Worker)
 */
export async function analyzeVisual(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/visual", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run performance/Core Web Vitals analysis (requires Browser Worker)
 */
export async function analyzePerformance(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/performance", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Deep single-page SEO analysis (comprehensive, all-in-one)
 * Covers on-page SEO, content quality, technical elements, schema, images, CWV
 * Equivalent to CLI command `/seo page <url>`
 */
export async function analyzePage(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/page", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run strategic SEO planning analysis
 * Creates industry-specific SEO strategy with templates
 */
export async function analyzePlan(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/plan", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Run programmatic SEO analysis and planning
 * Analyzes scale SEO opportunities and implementation strategies
 */
export async function analyzeProgrammatic(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/programmatic", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/**
 * Analyze competitor comparison pages for SEO, GEO, and AEO
 * Analyzes existing "X vs Y" and "Alternatives to X" pages on your site
 */
export async function analyzeCompetitorPages(url: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/competitor-pages", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

// ============================================================================
// Analysis Estimate API
// ============================================================================

export interface AnalysisEstimateRequest {
  url: string;
  analysis_mode: "individual" | "page_audit" | "site_audit";
  analysis_types?: string[]; // For individual mode
  max_pages?: number; // For site_audit mode
}

export interface AnalysisEstimateResponse {
  url: string;
  analysis_mode: string;
  analysis_types: string[];
  credits_required: number;
  cost_usd: number;
  breakdown: string;
}

/**
 * Estimate credits required for any analysis type
 *
 * Modes:
 * - individual: Select specific analysis types (1 credit each)
 * - page_audit: All 12 analysis types on one page (8 credits)
 * - site_audit: All 12 analysis types per page, site-wide (7 credits × pages)
 */
export async function estimateAnalysis(
  request: AnalysisEstimateRequest
): Promise<AnalysisEstimateResponse> {
  return apiRequest<AnalysisEstimateResponse>("/api/v1/analyze/estimate", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

// ============================================================================
// Analyses List API
// ============================================================================

export interface AnalysisListResponse {
  analyses: AnalysisResult[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface AnalysisResult {
  id: string;
  user_id: string;
  url: string;
  analysis_type: string;
  analysis_mode: "individual" | "page_audit" | "site_audit";
  credits_used: number;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  results_json: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisListParams {
  limit?: number;
  offset?: number;
  analysis_type?: string;
  analysis_mode?: "individual" | "page_audit" | "site_audit";
  status?: "pending" | "processing" | "completed" | "failed" | "cancelled";
}

/**
 * List user's analyses with optional filtering
 */
export async function listAnalyses(
  params: AnalysisListParams = {}
): Promise<AnalysisListResponse> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set("limit", params.limit.toString());
  if (params.offset) searchParams.set("offset", params.offset.toString());
  if (params.analysis_type) searchParams.set("analysis_type", params.analysis_type);
  if (params.analysis_mode) searchParams.set("analysis_mode", params.analysis_mode);
  if (params.status) searchParams.set("status", params.status);

  const queryString = searchParams.toString();
  return apiRequest<AnalysisListResponse>(
    `/api/v1/analyses${queryString ? `?${queryString}` : ""}`
  );
}

/**
 * Get status and results of a specific analysis
 */
export async function getAnalysisStatus(analysis_id: string): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>(`/api/v1/analyses/${analysis_id}`);
}

// ============================================================================
// Analysis Types Constants
// ============================================================================

/**
 * All available analysis types for individual reports
 */
export const ANALYSIS_TYPES = [
  "technical",
  "content",
  "schema",
  "geo",
  "sitemap",
  "hreflang",
  "images",
  "visual",
  "performance",
  "plan",
  "programmatic",
  "competitor-pages",
] as const;

export type AnalysisType = (typeof ANALYSIS_TYPES)[number];

/**
 * Human-readable labels for analysis types
 */
export const ANALYSIS_TYPE_LABELS: Record<AnalysisType, string> = {
  technical: "Technical SEO",
  content: "Content Quality (E-E-A-T)",
  schema: "Schema Markup",
  geo: "AI Search Optimization",
  sitemap: "Sitemap Analysis",
  hreflang: "International SEO",
  images: "Image Optimization",
  visual: "Visual Analysis",
  performance: "Core Web Vitals",
  plan: "Strategic SEO Planning",
  programmatic: "Programmatic SEO",
  "competitor-pages": "Competitor Comparison Pages",
};

// ============================================================================
// Credit Pricing Constants
// ============================================================================

/**
 * Credit pricing constants
 */
export const CREDIT_PRICING = {
  CREDITS_PER_DOLLAR: 8, // $1 = 8 credits
  INDIVIDUAL_REPORT: 1, // 1 credit per individual report
  PAGE_AUDIT: 8, // 8 credits for full page audit (all 12 types)
  SITE_AUDIT_PER_PAGE: 7, // 7 credits per page for site audits
  MINIMUM_TOPUP_DOLLARS: 8, // Minimum topup: $8
} as const;
