"use client";

import { SignInButton } from "@workos-inc/authkit-react";
import { Button } from "@/components/ui/button";

export function AuthButton() {
  return (
    <SignInButton
      provider="authkit"
      state={{
        // Optional state to pass through auth flow
        returnTo: typeof window !== "undefined" ? window.location.pathname : "/",
      }}
    >
      {(label) => (
        <Button variant="default" size="sm">
          {label}
        </Button>
      )}
    </SignInButton>
  );
}
