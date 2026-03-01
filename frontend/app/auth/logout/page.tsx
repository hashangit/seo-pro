"use client";

import { signOutAction } from "@/actions/auth";
import { useAuthUser } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { useTransition } from "react";

export default function LogoutPage() {
  const router = useRouter();
  const { loading } = useAuthUser();
  const [isPending, startTransition] = useTransition();

  const handleSignOut = () => {
    startTransition(() => {
      signOutAction();
    });
  };

  const isLoading = loading || isPending;

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="mx-auto max-w-md space-y-6 text-center">
        <h1 className="text-2xl font-bold">Sign Out</h1>
        <p className="text-muted-foreground">Are you sure you want to sign out?</p>
        <div className="flex justify-center gap-4">
          <Button onClick={handleSignOut} disabled={isLoading}>
            <LogOut className="mr-2 h-4 w-4" />
            {isLoading ? "Signing out..." : "Sign Out"}
          </Button>
          <Button variant="outline" onClick={() => router.push("/")}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
