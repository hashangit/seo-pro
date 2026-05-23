"use client";

import { useCreditBalance } from "@/hooks/use-queries";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { useAuthUser } from "@/hooks/use-auth";

export function CreditBalance() {
  const { isAuthenticated } = useAuthUser();
  const { data, isLoading } = useCreditBalance();

  if (isLoading) {
    return (
      <div className="h-8 w-20 animate-pulse rounded-md bg-muted" />
    );
  }

  if (!isAuthenticated || typeof data?.balance !== "number") {
    return (
      <Link href="/credits">
        <Badge variant="secondary" className="cursor-pointer">
          Get Credits
        </Badge>
      </Link>
    );
  }

  const balance = data.balance;

  return (
    <Link href="/credits">
      <Badge variant={balance > 0 ? "default" : "destructive"} className="cursor-pointer">
        {balance} credit{balance !== 1 ? "s" : ""}
      </Badge>
    </Link>
  );
}
