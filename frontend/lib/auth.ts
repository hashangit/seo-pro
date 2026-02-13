/**
 * Authentication utilities and hooks for WorkOS AuthKit
 *
 * This module provides React hooks and utilities for working with
 * WorkOS authentication throughout the application.
 */

"use client";

import { useEffect, useState, useCallback } from "react";

/**
 * User information from WorkOS
 */
export interface WorkOSUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  /**
   * The organization ID the user belongs to (if any)
   */
  organizationId?: string;
}

/**
 * Authentication state
 */
export interface AuthState {
  user: WorkOSUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error?: string;
}

/**
 * Hook to get the current authentication state
 *
 * This hook provides the current user, loading state, and authentication status.
 * It automatically refreshes when the authentication state changes.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { user, isLoading, isAuthenticated } = useAuth();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (!isAuthenticated) return <div>Please sign in</div>;
 *
 *   return <div>Welcome, {user.email}</div>;
 * }
 * ```
 */
export function useAuth(): AuthState {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Refresh auth state
  const refresh = useCallback(async () => {
    try {
      const { getUser } = await import("@workos-inc/authkit-react");
      const user = await getUser();

      setState({
        user: user ? {
          id: user.id,
          email: user.email,
          firstName: user.firstName ?? undefined,
          lastName: user.lastName ?? undefined,
          organizationId: (user as any).organizationId,
        } : null,
        isLoading: false,
        isAuthenticated: !!user,
      });
    } catch (error) {
      console.error("Failed to get auth state:", error);
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
        error: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }, []);

  useEffect(() => {
    refresh();

    // Listen for storage changes (sign in/sign out from other tabs)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "workos-auth-state") {
        refresh();
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [refresh]);

  return state;
}

/**
 * Hook to get the sign-in URL
 *
 * @param returnTo - The URL to redirect to after sign in
 * @returns The sign-in URL or null if not configured
 */
export function useSignInUrl(returnTo?: string): string | null {
  const [signInUrl, setSignInUrl] = useState<string | null>(null);

  useEffect(() => {
    import("@workos-inc/authkit-react")
      .then(({ getSignInUrl }) => {
        getSignInUrl({ state: { returnTo } }).then(setSignInUrl);
      })
      .catch((error) => {
        console.error("Failed to get sign-in URL:", error);
      });
  }, [returnTo]);

  return signInUrl;
}

/**
 * Hook to get the sign-up URL
 *
 * @param returnTo - The URL to redirect to after sign up
 * @returns The sign-up URL or null if not configured
 */
export function useSignUpUrl(returnTo?: string): string | null {
  const [signUpUrl, setSignUpUrl] = useState<string | null>(null);

  useEffect(() => {
    import("@workos-inc/authkit-react")
      .then(({ getSignUpUrl }) => {
        getSignUpUrl({ state: { returnTo } }).then(setSignUpUrl);
      })
      .catch((error) => {
        console.error("Failed to get sign-up URL:", error);
      });
  }, [returnTo]);

  return signUpUrl;
}

/**
 * Higher-order component that requires authentication
 *
 * Redirects to sign-in if the user is not authenticated.
 *
 * @example
 * ```tsx
 * const ProtectedPage = requireAuth(function ProtectedPage() {
 *   return <div>Protected content</div>;
 * });
 * ```
 */
export function requireAuth<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ComponentType
): React.ComponentType<P> {
  return function AuthRequired(props: P) {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
      return <div className="flex min-h-screen items-center justify-center">Loading...</div>;
    }

    if (!isAuthenticated) {
      if (fallback) {
        const FallbackComponent = fallback;
        return <FallbackComponent />;
      }
      // Redirect to sign-in - the SignInButton will handle this
      return (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <p className="mb-4 text-muted-foreground">Please sign in to continue</p>
            <a href="/auth/login" className="text-blue-600 hover:underline">
              Sign In
            </a>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };
}
