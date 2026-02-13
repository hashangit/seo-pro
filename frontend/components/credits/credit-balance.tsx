"use client";

import { useEffect, useState } from "react";
import { getCreditBalance } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export function CreditBalance() {
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBalance() {
      try {
        const data = await getCreditBalance();
        setBalance(data.balance);
      } catch {
        // Not logged in or error
        setBalance(0);
      } finally {
        setLoading(false);
      }
    }
    fetchBalance();
  }, []);

  if (loading) {
    return (
      <div className="h-8 w-20 animate-pulse rounded-md bg-muted" />
    );
  }

  if (balance === null) {
    return (
      <Link href="/credits/purchase">
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
