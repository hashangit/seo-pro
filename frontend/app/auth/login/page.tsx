"use client";

import { useAuth } from "@workos-inc/authkit-react";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { signIn, user, isLoading } = useAuth();
  const router = useRouter();

  // Redirect if already authenticated
  useEffect(() => {
    if (user && !isLoading) {
      router.push("/");
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 rounded-lg border p-8 shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold">SEO Pro</h1>
          <p className="mt-2 text-muted-foreground">
            Sign in to access your dashboard
          </p>
        </div>
        <div className="flex justify-center">
          <Button
            size="lg"
            onClick={() => signIn()}
            disabled={isLoading}
          >
            <LogIn className="mr-2 h-4 w-4" />
            Sign In with WorkOS
          </Button>
        </div>
      </div>
    </div>
  );
}
