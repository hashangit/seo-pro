'use client';

import { useAccessToken, useAuth } from '@workos-inc/authkit-nextjs/components';

export interface AuthUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

export function useAuthUser() {
  const { user, loading } = useAuth();
  const { getAccessToken, loading: accessTokenLoading } = useAccessToken();

  return {
    user: user as AuthUser | null,
    loading,
    accessTokenLoading,
    isAuthenticated: !!user,
    getAccessToken,
  };
}
