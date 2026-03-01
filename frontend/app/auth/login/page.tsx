"use client";

import { useAuthUser } from "@/hooks/use-auth";
import { signInAction } from "@/actions/auth";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { user, loading } = useAuthUser();
  const router = useRouter();

  // Redirect if already authenticated
  useEffect(() => {
    if (user && !loading) {
      router.push("/");
    }
  }, [user, loading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 rounded-lg border p-8 shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold">SEO Pro</h1>
          <p className="mt-2 text-muted-foreground">
            Sign in to access your dashboard
          </p>
        </div>
        <form action={signInAction} className="flex justify-center">
          <Button type="submit" size="lg" disabled={loading}>
            <LogIn className="mr-2 h-4 w-4" />
            Sign In with WorkOS
          </Button>
        </form>
      </div>
    </div>
  );
}
