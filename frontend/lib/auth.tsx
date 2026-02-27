/**
 * Authentication utilities and hooks for WorkOS AuthKit
 *
 * This module re-exports and extends WorkOS AuthKit functionality
 * for use throughout the application.
 */

"use client";

import { useEffect, useRef, useCallback } from "react";
import { useAuth as useAuthKit, AuthKitProvider } from "@workos-inc/authkit-react";

// Re-export AuthKitProvider for app setup
export { AuthKitProvider };

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
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string>;
}

/**
 * Hook to get the current authentication state
 *
 * This hook wraps the WorkOS AuthKit useAuth hook and provides
 * a simplified interface for the application.
 * Includes automatic token refresh before expiration.
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
  const auth = useAuthKit();
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const user: WorkOSUser | null = auth.user ? {
    id: auth.user.id,
    email: auth.user.email,
    firstName: auth.user.firstName ?? undefined,
    lastName: auth.user.lastName ?? undefined,
    organizationId: auth.organizationId ?? undefined,
  } : null;

  // Token refresh logic - checks every minute and refreshes if needed
  const checkAndRefreshToken = useCallback(async () => {
    if (!auth.user) return;

    try {
      // WorkOS AuthKit handles token refresh automatically when getAccessToken is called
      // This proactively refreshes to prevent expiration during user activity
      await auth.getAccessToken();
    } catch (error) {
      console.error("Token refresh failed:", error);
      // If refresh fails, the user will be redirected to login on next API call
    }
  }, [auth]);

  // Set up token refresh interval
  useEffect(() => {
    if (auth.user) {
      // Check token every minute
      refreshIntervalRef.current = setInterval(checkAndRefreshToken, 60000);

      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [auth.user, checkAndRefreshToken]);

  return {
    user,
    isLoading: auth.isLoading,
    isAuthenticated: !!auth.user,
    signIn: auth.signIn,
    signOut: auth.signOut,
    getAccessToken: auth.getAccessToken,
  };
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
      // Redirect to sign-in
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
