'use client';

import { useAuthUser } from '@/hooks/use-auth';
import { signOutAction } from '@/actions/auth';
import { Button } from '@/components/ui/button';
import { LogIn, LogOut } from 'lucide-react';

interface AuthButtonProps {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
}

export function AuthButton({ variant = 'default', size = 'sm' }: AuthButtonProps) {
  const { user, loading, isAuthenticated } = useAuthUser();

  if (loading) {
    return (
      <Button variant={variant} size={size} disabled>
        Loading...
      </Button>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <Button variant={variant} size={size} asChild>
        <a href="/login">
          <LogIn className="mr-2 h-4 w-4" />
          Sign In
        </a>
      </Button>
    );
  }

  return (
    <form action={signOutAction}>
      <Button variant="outline" size={size} type="submit">
        <LogOut className="mr-2 h-4 w-4" />
        Sign Out ({user.firstName || user.email})
      </Button>
    </form>
  );
}
