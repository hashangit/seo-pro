'use client';

import { useAuth } from '@workos-inc/authkit-nextjs/components';
import { useAccessToken } from '@workos-inc/authkit-nextjs/components';

export interface AuthUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

export function useAuthUser() {
  const { user, loading } = useAuth();
  const { getAccessToken } = useAccessToken();

  return {
    user: user as AuthUser | null,
    loading,
    isAuthenticated: !!user,
    getAccessToken,
  };
}
