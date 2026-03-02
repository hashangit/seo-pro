import { withAuth } from '@workos-inc/authkit-nextjs';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const auth = await withAuth();
  const token = auth.accessToken;

  if (!token) {
    throw new ApiError(401, 'Unauthorized: No session');
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (response.status === 401) {
    throw new ApiError(401, 'Unauthorized: Session expired');
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      response.status,
      `API Error: ${response.status} - ${errorText}`
    );
  }

  return response.json();
}

// Typed response interfaces
export interface CreditBalanceResponse {
  balance: number;
}

export interface AuditListResponse {
  audits: Array<{
    id: string;
    url: string;
    status: string;
    created_at: string;
    completed_at: string | null;
  }>;
  total: number;
}

export interface CreditRequest {
  id: string;
  user_id: string;
  credits_requested: number;
  amount: number;
  currency: string;
  status: string;
  invoice_number: string | null;
  payment_proof_url: string | null;
  payment_notes: string | null;
  admin_notes: string | null;
  created_at: string;
  users?: {
    email: string;
  };
}

// Credit API functions
export async function getCreditBalance(): Promise<CreditBalanceResponse> {
  return apiRequest<CreditBalanceResponse>('/api/v1/credits/balance');
}

export async function useCredits(
  amount: number,
  reason: string
): Promise<{ success: boolean; newBalance: number }> {
  return apiRequest<{ success: boolean; newBalance: number }>(
    '/api/v1/credits/use',
    {
      method: 'POST',
      body: JSON.stringify({ amount, reason }),
    }
  );
}

// Audit API functions
export async function listAudits(
  limit: number = 100,
  offset: number = 0
): Promise<AuditListResponse> {
  return apiRequest<AuditListResponse>(
    `/api/v1/audits?limit=${limit}&offset=${offset}`
  );
}

export async function getAudit(id: string): Promise<{ audit: AuditListResponse['audits'][0] }> {
  return apiRequest<{ audit: AuditListResponse['audits'][0] }>(
    `/api/v1/audits/${id}`
  );
}

// Admin API functions
export async function adminGetCreditRequests(
  status?: string,
  limit: number = 50,
  offset: number = 0
): Promise<{ requests: CreditRequest[]; total: number }> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (status) {
    params.append('status', status);
  }
  return apiRequest<{ requests: CreditRequest[]; total: number }>(
    `/api/v1/admin/credit-requests?${params}`
  );
}

export async function adminApproveCreditRequest(
  requestId: string
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(
    `/api/v1/admin/credit-requests/${requestId}/approve`,
    { method: 'POST' }
  );
}
