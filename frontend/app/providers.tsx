"use client";

import { AuthKitProvider } from "@workos-inc/authkit-react";
import { ReactNode } from "react";

interface ProvidersProps {
  children: ReactNode;
  clientId: string | undefined;
  redirectUri: string | undefined;
}

export function Providers({ children, clientId, redirectUri }: ProvidersProps) {
  // Use a placeholder clientId during build/when not configured
  // devMode ensures no real API calls are made
  const effectiveClientId = clientId || "placeholder-build-time-client-id";

  return (
    <AuthKitProvider
      clientId={effectiveClientId}
      redirectUri={redirectUri ? `${redirectUri}/auth/callback` : "http://localhost:3000/auth/callback"}
      devMode={true}
    >
      {children}
    </AuthKitProvider>
  );
}
