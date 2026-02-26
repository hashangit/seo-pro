"use client";

import React from "react";
import { AuthKitProvider } from "@workos-inc/authkit-react";

interface ProvidersProps {
  children: React.ReactNode;
  clientId: string;
  redirectUri: string;
}

export function Providers({ children, clientId, redirectUri }: ProvidersProps) {
  return (
    <AuthKitProvider
      clientId={clientId}
      redirectUri={redirectUri}
      devMode={process.env.NEXT_PUBLIC_DEV_MODE === "true"}
    >
      {children}
    </AuthKitProvider>
  );
}
