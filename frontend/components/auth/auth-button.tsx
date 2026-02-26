"use client";

import { useAuth } from "@workos-inc/authkit-react";
import { Button } from "@/components/ui/button";
import { LogIn, LogOut } from "lucide-react";

interface AuthButtonProps {
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
}

export function AuthButton({ variant = "default", size = "sm" }: AuthButtonProps) {
  const { user, signIn, signOut, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Button variant={variant} size={size} disabled>
        Loading...
      </Button>
    );
  }

  if (user) {
    return (
      <Button
        variant="outline"
        size={size}
        onClick={() => signOut()}
      >
        <LogOut className="mr-2 h-4 w-4" />
        Sign Out
      </Button>
    );
  }

  return (
    <Button
      variant={variant}
      size={size}
      onClick={() => signIn()}
    >
      <LogIn className="mr-2 h-4 w-4" />
      Sign In
    </Button>
  );
}
