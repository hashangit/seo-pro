"use client";

import { useEffect, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { getCreditHistory } from "@/lib/api";
import { logger, LogContext } from "@/lib/logger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Minus, Plus, Loader2 } from "lucide-react";
import Link from "next/link";

type Transaction = {
  id: string;
  amount: number;
  balance_after: number;
  transaction_type: "purchase" | "spend" | "refund" | "bonus";
  description: string | null;
  created_at: string;
};

export default function CreditsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState<number | null>(null);
  const [isPending, startTransition] = useTransition();

  const fetchHistory = async () => {
    try {
      const data = await getCreditHistory();
      setTransactions(data.transactions || []);
      setBalance(
        data.transactions?.[0]?.balance_after || 0
      );
    } catch (err) {
      logger.error(LogContext.CREDITS, err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    startTransition(() => fetchHistory());
  }, []);

  const handleRefresh = () => {
    startTransition(() => fetchHistory());
  };

  const getTransactionIcon = (type: string) => {
    if (type === "purchase" || type === "bonus") {
      return <Plus className="h-4 w-4 text-green-600" />;
    }
    return <Minus className="h-4 w-4 text-red-600" />;
  };

  const getTransactionVariant = (type: string) => {
    if (type === "purchase" || type === "bonus") {
      return "default";
    }
    return "secondary";
  };

  if (loading && transactions.length === 0) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6 flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Credit History</h1>
          </div>
          <div className="animate-pulse space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-20 rounded-lg bg-muted" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Credits</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isPending}
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Refresh"
              )}
            </Button>
            {balance !== null && (
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Current Balance</p>
                <p className="text-2xl font-bold">{balance} credits</p>
              </div>
            )}
          </div>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Purchased</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {transactions.filter((t) => t.amount > 0).reduce((sum, t) => sum + t.amount, 0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Spent</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {Math.abs(transactions.filter((t) => t.amount < 0).reduce((sum, t) => sum + t.amount, 0))}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Buy Credits</CardTitle>
            </CardHeader>
            <CardContent>
              <Link href="/credits">
                <Button className="w-full">Purchase</Button>
              </Link>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Requests</CardTitle>
            </CardHeader>
            <CardContent>
              <Link href="/credits/requests">
                <Button variant="outline" className="w-full">View Requests</Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Transaction History */}
        <Card>
          <CardHeader>
            <CardTitle>Transaction History</CardTitle>
          </CardHeader>
          <CardContent>
            {transactions.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">
                No transactions yet. Purchase credits to get started!
              </p>
            ) : (
              <div className="space-y-1">
                {transactions.map((transaction) => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between border-b py-3 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      {getTransactionIcon(transaction.transaction_type)}
                      <div>
                        <p className="font-medium">
                          {transaction.description ||
                            transaction.transaction_type.charAt(0).toUpperCase() +
                            transaction.transaction_type.slice(1)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(transaction.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={getTransactionVariant(transaction.transaction_type)}>
                        {transaction.amount > 0 ? "+" : ""}
                        {transaction.amount} credits
                      </Badge>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Balance: {transaction.balance_after}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
