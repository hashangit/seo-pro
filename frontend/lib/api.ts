/**
 * API Client for SEO Pro Backend
 *
 * Handles all communication with the FastAPI backend.
 * Authentication is handled via React components using useAuth hook.
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
 * Make API request with optional authentication
 *
 * @param endpoint - API endpoint path
 * @param options - Fetch options
 * @param token - Optional auth token (obtained from useAuth hook)
 * @throws {AuthError} If authentication fails (401/403 responses)
 * @throws {Error} For other API errors
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Copy existing headers if they're a plain object
  if (options.headers && typeof options.headers === "object") {
    const existingHeaders = options.headers as Record<string, string>;
    Object.keys(existingHeaders).forEach(key => {
      headers[key] = existingHeaders[key];
    });
  }

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

export async function getCreditBalance(token?: string): Promise<CreditBalanceResponse> {
  return apiRequest<CreditBalanceResponse>("/api/v1/credits/balance", {}, token);
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
  request: AuditEstimateRequest,
  token?: string
): Promise<AuditEstimateResponse> {
  return apiRequest<AuditEstimateResponse>("/api/v1/audit/estimate", {
    method: "POST",
    body: JSON.stringify(request),
  }, token);
}

// ============================================================================
// URL Discovery API
// ============================================================================

export interface URLDiscoveryRequest {
  url: string;
  sitemap_url?: string;
}

export interface URLDiscoveryResponse {
  urls: string[];
  source: "sitemap" | "homepage" | "manual_sitemap" | "error";
  confidence: number;
  sitemap_found: boolean;
  sitemap_url: string | null;
  warning?: string;
  error?: string;
}

export async function discoverSiteURLs(
  request: URLDiscoveryRequest,
  token?: string
): Promise<URLDiscoveryResponse> {
  return apiRequest<URLDiscoveryResponse>("/api/v1/audit/discover", {
    method: "POST",
    body: JSON.stringify(request),
  }, token);
}

export interface AuditRunRequest {
  quote_id: string;
  selected_urls?: string[];
}

export interface AuditRunResponse {
  audit_id: string;
  status: string;
}

export async function runAudit(
  quote_id: string,
  selected_urls?: string[],
  token?: string
): Promise<AuditRunResponse> {
  return apiRequest<AuditRunResponse>("/api/v1/audit/run", {
    method: "POST",
    body: JSON.stringify({ quote_id, selected_urls }),
  }, token);
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
  audit_id: string,
  token?: string
): Promise<AuditStatusResponse> {
  return apiRequest<AuditStatusResponse>(`/api/v1/audit/${audit_id}`, {}, token);
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
  offset: number = 0,
  token?: string
): Promise<AuditListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString()
  });
  return apiRequest<AuditListResponse>(`/api/v1/audit?${params}`, {}, token);
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

export async function getCreditHistory(token?: string): Promise<CreditHistoryResponse> {
  return apiRequest<CreditHistoryResponse>("/api/v1/credits/history", {}, token);
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
export async function analyzeTechnical(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/technical", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run content quality (E-E-A-T) analysis
 */
export async function analyzeContent(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/content", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run schema markup analysis
 */
export async function analyzeSchema(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/schema", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run GEO (AI Search) optimization analysis
 */
export async function analyzeGeo(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/geo", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run sitemap analysis
 */
export async function analyzeSitemap(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/sitemap", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run hreflang/international SEO analysis
 */
export async function analyzeHreflang(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/hreflang", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run image SEO analysis
 */
export async function analyzeImages(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/images", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run visual SEO analysis (requires Browser Worker)
 */
export async function analyzeVisual(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/visual", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run performance/Core Web Vitals analysis (requires Browser Worker)
 */
export async function analyzePerformance(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/performance", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Deep single-page SEO analysis (comprehensive, all-in-one)
 * Covers on-page SEO, content quality, technical elements, schema, images, CWV
 * Equivalent to CLI command `/seo page <url>`
 */
export async function analyzePage(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/page", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run strategic SEO planning analysis
 * Creates industry-specific SEO strategy with templates
 */
export async function analyzePlan(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/plan", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Run programmatic SEO analysis and planning
 * Analyzes scale SEO opportunities and implementation strategies
 */
export async function analyzeProgrammatic(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/programmatic", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

/**
 * Analyze competitor comparison pages for SEO, GEO, and AEO
 * Analyzes existing "X vs Y" and "Alternatives to X" pages on your site
 */
export async function analyzeCompetitorPages(url: string, token?: string): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/analyze/competitor-pages", {
    method: "POST",
    body: JSON.stringify({ url }),
  }, token);
}

// ============================================================================
// Analysis Estimate API
// ============================================================================

export interface AnalysisEstimateRequest {
  url: string;
  analysis_mode: "individual" | "page_audit" | "site_audit";
  analysis_types?: string[]; // For individual mode
  max_pages?: number; // For site_audit mode (deprecated)
  selected_urls?: string[]; // For site_audit mode, pre-selected URLs
}

export interface AnalysisEstimateResponse {
  url: string;
  analysis_mode: string;
  analysis_types: string[];
  credits_required: number;
  cost_usd: number;
  breakdown: string;
  estimated_pages?: number; // For site_audit mode
  quote_id?: string; // For site_audit mode
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
  request: AnalysisEstimateRequest,
  token?: string
): Promise<AnalysisEstimateResponse> {
  return apiRequest<AnalysisEstimateResponse>("/api/v1/analyze/estimate", {
    method: "POST",
    body: JSON.stringify(request),
  }, token);
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
  params: AnalysisListParams = {},
  token?: string
): Promise<AnalysisListResponse> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set("limit", params.limit.toString());
  if (params.offset) searchParams.set("offset", params.offset.toString());
  if (params.analysis_type) searchParams.set("analysis_type", params.analysis_type);
  if (params.analysis_mode) searchParams.set("analysis_mode", params.analysis_mode);
  if (params.status) searchParams.set("status", params.status);

  const queryString = searchParams.toString();
  return apiRequest<AnalysisListResponse>(
    `/api/v1/analyses${queryString ? `?${queryString}` : ""}`,
    {},
    token
  );
}

/**
 * Get status and results of a specific analysis
 */
export async function getAnalysisStatus(analysis_id: string, token?: string): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>(`/api/v1/analyses/${analysis_id}`, {}, token);
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
