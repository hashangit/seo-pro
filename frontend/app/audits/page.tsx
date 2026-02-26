"use client";

import { useEffect, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { listAudits, type AuditStatusResponse } from "@/lib/api";
import { logger, LogContext } from "@/lib/logger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";

export default function AuditsPage() {
  const [audits, setAudits] = useState<AuditStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [isPending, startTransition] = useTransition();
  const limit = 20;

  async function fetchAudits(offset: number) {
    try {
      setLoading(true);
      const data = await listAudits(limit, offset);
      setAudits(data.audits || []);
      setTotal(data.total || 0);
    } catch (err) {
      logger.error(LogContext.AUDIT, err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAudits(0);
  }, []);

  const loadMore = () => {
    const nextOffset = (page + 1) * limit;
    startTransition(() => {
      fetchAudits(nextOffset);
      setPage(page + 1);
    });
  };

  const isLoading = loading || isPending;

  if (loading && audits.length === 0) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Audits</h1>
            <div className="text-right">
              {total !== null && (
                <p className="text-sm text-muted-foreground">Total: {total}</p>
              )}
            </div>
          </div>

          <div className="mb-6">
            <Card>
              <CardHeader>
                <CardTitle>Filters</CardTitle>
              </CardHeader>
              <CardContent className="flex gap-4">
                <Button variant="outline" size="sm" onClick={() => setPage(0)}>
                  All
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage(1)}>
                  Completed
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage(2)}>
                  Failed
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="py-8">
                  <div className="animate-pulse space-y-2">
                    <div className="h-4 w-1/3 rounded bg-muted" />
                    <div className="h-3 w-1/4 rounded bg-muted" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">Audits</h1>
          <div className="text-right">
            {total !== null && (
              <p className="text-sm text-muted-foreground">Total: {total}</p>
            )}
          </div>
        </div>

        <div className="mb-6">
          <Card>
            <CardHeader>
              <CardTitle>Filters</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-4">
              <Button variant="outline" size="sm" onClick={() => setPage(0)}>
                All
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage(1)}>
                Completed
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage(2)}>
                Failed
              </Button>
            </CardContent>
          </Card>
        </div>

        {audits.length === 0 && !isLoading && (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-muted-foreground">No audits yet. Run an audit to get started!</p>
            </CardContent>
          </Card>
        )}

        <div className="space-y-4">
          {audits.map((audit) => (
            <Card key={audit.id}>
              <CardHeader className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{audit.url}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(audit.created_at)}
                  </p>
                </div>
                <Badge
                  variant={
                    audit.status === "completed"
                      ? "default"
                      : audit.status === "failed"
                      ? "destructive"
                      : "secondary"
                  }
                >
                  {audit.status}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium">Credits Used</p>
                    <p className="text-2xl font-bold">{audit.credits_used}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Pages</p>
                    <p className="text-2xl font-bold">{audit.page_count}</p>
                  </div>
                </div>

                {audit.status === "completed" && audit.results && (
                  <Button variant="outline" size="sm" className="w-full">
                    View Results
                  </Button>
                )}

                {audit.status === "failed" && audit.error_message && (
                  <p className="text-sm text-destructive mt-2">
                    Error: {audit.error_message}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {!isLoading && audits.length >= limit && total && total > (page + 1) * limit && (
          <div className="mt-6 text-center">
            <Button onClick={loadMore} variant="outline" size="lg" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Loading...
                </>
              ) : (
                "Load More"
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
