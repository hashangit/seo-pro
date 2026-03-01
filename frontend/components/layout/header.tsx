"use client";

import Link from "next/link";
import { CreditBalance } from "@/components/credits/credit-balance";
import { AuthButton } from "@/components/auth/auth-button";
import { SEOLogo } from "@/components/marketing/seo-logo";
import { useAuthUser } from "@/hooks/use-auth";
import { signOutAction } from "@/actions/auth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { User, LogOut } from "lucide-react";
import { useTransition } from "react";

export function Header() {
  const { user, loading } = useAuthUser();
  const isAuthenticated = !!user;
  const [isPending, startTransition] = useTransition();

  const handleSignOut = () => {
    startTransition(() => {
      signOutAction();
    });
  };

  const isLoading = loading || isPending;

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center px-4">
        <div className="flex items-center gap-8">
          <Link href="/">
            <SEOLogo />
          </Link>
          <nav className="hidden md:flex gap-6">
            <Link
              href="/features"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Features
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Pricing
            </Link>
            <Link
              href="/docs"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Documentation
            </Link>
          </nav>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <CreditBalance />
          {isLoading ? (
            <div className="h-8 w-20 animate-pulse rounded bg-muted" />
          ) : isAuthenticated && user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline">
                    {user.firstName || user.email.split("@")[0]}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="flex flex-col space-y-1 p-2">
                  <p className="text-sm font-medium">{user.email}</p>
                  {user.firstName && user.lastName && (
                    <p className="text-xs text-muted-foreground">
                      {user.firstName} {user.lastName}
                    </p>
                  )}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/dashboard" className="cursor-pointer">
                    Dashboard
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings" className="cursor-pointer">
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleSignOut}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <AuthButton />
          )}
        </div>
      </div>
    </header>
  );
}
