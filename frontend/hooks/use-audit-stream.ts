"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthUser } from "@/hooks/use-auth";

const WS_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function useWebSocketStream<T>(
  auditId: string,
  queryKey: unknown[],
  enabled: boolean
) {
  const queryClient = useQueryClient();
  const { isAuthenticated, getAccessToken } = useAuthUser();
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (!enabled || !isAuthenticated || !auditId) return;

    let cancelled = false;

    async function connect() {
      if (cancelled) return;

      const token = await getAccessToken();
      if (cancelled) return;

      const wsUrl = WS_URL.replace(/^http/, "ws");
      const socket = new WebSocket(
        `${wsUrl}/api/v1/audit/${auditId}/stream?token=${token}`
      );
      socketRef.current = socket;

      socket.onmessage = (event) => {
        if (cancelled) return;
        const data = JSON.parse(event.data);
        if (data.type === "ping") return;

        queryClient.setQueryData(queryKey, (old: unknown) => {
          if (!old || typeof old !== "object") return data;
          return { ...(old as Record<string, unknown>), ...data };
        });
      };

      socket.onclose = (event) => {
        if (cancelled) return;
        if (event.code !== 1000) {
          reconnectTimerRef.current = setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      socketRef.current?.close();
      clearTimeout(reconnectTimerRef.current);
    };
  }, [auditId, enabled, isAuthenticated, getAccessToken, queryClient, queryKey]);
}

export function useAuditStream(auditId: string, enabled = true) {
  useWebSocketStream(auditId, ["audit", auditId], enabled);
}

export function useAnalysisStream(analysisId: string, enabled = true) {
  useWebSocketStream(analysisId, ["analysis", analysisId], enabled);
}
