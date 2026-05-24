"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthUser } from "@/hooks/use-auth";
import {
  getCreditBalance,
  getCreditHistory,
  getCreditRequests,
  createCreditRequest,
  submitPaymentProof,
  listAudits,
  getAuditStatus,
  listAnalyses,
  getAnalysisStatus,
  type CreditRequestCreate,
  type PaymentProofUpload,
  type AnalysisListParams,
} from "@/lib/api";

// ============================================================================
// Token helpers
// ============================================================================

function useToken() {
  const { isAuthenticated, accessTokenLoading, getAccessToken } = useAuthUser();
  return {
    canFetch: isAuthenticated && !accessTokenLoading,
    getToken: async () => isAuthenticated ? getAccessToken() : undefined,
  };
}

// ============================================================================
// Credit queries
// ============================================================================

export function useCreditBalance() {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["creditBalance"],
    queryFn: async () => {
      const token = await getToken();
      return getCreditBalance(token);
    },
    enabled: canFetch,
    staleTime: 30_000,
  });
}

export function useCreditHistory() {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["creditHistory"],
    queryFn: async () => {
      const token = await getToken();
      return getCreditHistory(token);
    },
    enabled: canFetch,
  });
}

export function useCreditRequests(limit = 50, offset = 0) {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["creditRequests", limit, offset],
    queryFn: async () => {
      const token = await getToken();
      return getCreditRequests(limit, offset, token);
    },
    enabled: canFetch,
  });
}

// ============================================================================
// Credit mutations
// ============================================================================

export function useCreateCreditRequest() {
  const queryClient = useQueryClient();
  const { getToken } = useToken();

  return useMutation({
    mutationFn: async (request: CreditRequestCreate) => {
      const token = await getToken();
      return createCreditRequest(request, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["creditRequests"] });
      queryClient.invalidateQueries({ queryKey: ["creditBalance"] });
      queryClient.invalidateQueries({ queryKey: ["creditHistory"] });
    },
  });
}

export function useSubmitPaymentProof() {
  const queryClient = useQueryClient();
  const { getToken } = useToken();

  return useMutation({
    mutationFn: async ({ requestId, proof }: { requestId: string; proof: PaymentProofUpload }) => {
      const token = await getToken();
      return submitPaymentProof(requestId, proof, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["creditRequests"] });
    },
  });
}

// ============================================================================
// Audit queries
// ============================================================================

export function useAuditsList(limit = 20, offset = 0) {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["audits", limit, offset],
    queryFn: async () => {
      const token = await getToken();
      return listAudits(limit, offset, token);
    },
    enabled: canFetch,
  });
}

export function useAuditStatus(auditId: string) {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["audit", auditId],
    queryFn: async () => {
      const token = await getToken();
      return getAuditStatus(auditId, token);
    },
    enabled: canFetch && !!auditId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2000;
    },
  });
}

// ============================================================================
// Analysis queries
// ============================================================================

export function useAnalysesList(params: AnalysisListParams = {}) {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["analyses", params],
    queryFn: async () => {
      const token = await getToken();
      return listAnalyses(params, token);
    },
    enabled: canFetch,
  });
}

export function useAnalysisStatus(analysisId: string) {
  const { canFetch, getToken } = useToken();
  return useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: async () => {
      const token = await getToken();
      return getAnalysisStatus(analysisId, token);
    },
    enabled: canFetch && !!analysisId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" || status === "cancelled"
        ? false
        : 5000;
    },
  });
}
