"use client";

import { useEffect, useState } from "react";
import { getCreditBalance } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { useAuthUser } from "@/hooks/use-auth";

export function CreditBalance() {
  const { isAuthenticated, getAccessToken } = useAuthUser();
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBalance() {
      if (!isAuthenticated) {
        setBalance(null);
        setLoading(false);
        return;
      }

      try {
        const token = await getAccessToken();
        const data = await getCreditBalance(token);
        setBalance(data.balance);
      } catch {
        // Not logged in or error
        setBalance(null);
      } finally {
        setLoading(false);
      }
    }
    fetchBalance();
  }, [isAuthenticated, getAccessToken]);

  if (loading) {
    return (
      <div className="h-8 w-20 animate-pulse rounded-md bg-muted" />
    );
  }

  if (balance === null) {
    return (
      <Link href="/credits">
        <Badge variant="secondary" className="cursor-pointer">
          Get Credits
        </Badge>
      </Link>
    );
  }

  return (
    <Link href="/credits">
      <Badge variant={balance > 0 ? "default" : "destructive"} className="cursor-pointer">
        {balance} credit{balance !== 1 ? "s" : ""}
      </Badge>
    </Link>
  );
}
