"use client";

import { SignOutButton } from "@workos-inc/authkit-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function LogoutPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="mx-auto max-w-md space-y-6 text-center">
        <h1 className="text-2xl font-bold">Sign Out</h1>
        <p className="text-muted-foreground">Are you sure you want to sign out?</p>
        <div className="flex justify-center gap-4">
          <SignOutButton>
            {(label) => (
              <Button onClick={() => router.push("/")}>{label}</Button>
            )}
          </SignOutButton>
          <Button variant="outline" onClick={() => router.push("/")}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
