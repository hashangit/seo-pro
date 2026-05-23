"use client";

import { useParams } from "next/navigation";
import { useAuditStatus } from "@/hooks/use-queries";
import { useAuditStream } from "@/hooks/use-audit-stream";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export default function AuditPage() {
  const params = useParams();
  const auditId = params.id as string;

  const { data: audit, isLoading } = useAuditStatus(auditId);
  useAuditStream(auditId, !isLoading && audit?.status !== "completed" && audit?.status !== "failed");

  const statusColors = {
    queued: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-sm text-muted-foreground">Loading audit status...</p>
        </div>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto mb-4 h-12 w-12 text-destructive" />
          <h1 className="mb-2 text-2xl font-bold">Audit Not Found</h1>
          <p className="text-muted-foreground">
            The audit you&apos;re looking for doesn&apos;t exist or may have been deleted.
          </p>
        </div>
      </div>
    );
  }

  const isActive = audit.status !== "completed" && audit.status !== "failed";

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">SEO Audit Results</h1>
            <p className="text-muted-foreground">{audit.url}</p>
          </div>
          <div className="flex items-center gap-2">
            {isActive && (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            )}
            <Badge
              className={`text-sm ${statusColors[audit.status as keyof typeof statusColors]}`}
            >
              {audit.status.charAt(0).toUpperCase() + audit.status.slice(1)}
            </Badge>
          </div>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Pages Analyzed</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{audit.page_count}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Credits Used</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{audit.credits_used}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Created</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                {new Date(audit.created_at).toLocaleString()}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                {audit.completed_at
                  ? new Date(audit.completed_at).toLocaleString()
                  : "In progress..."}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        {audit.status === "completed" && (audit as any).results && (
          <div className="space-y-6">
            {((audit as any).results as any)?.technical && (
              <Card>
                <CardHeader>
                  <CardTitle>Technical SEO</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {((audit as any).results as any).technical.passes?.map((item: any) => (
                      <div key={item.check} className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <span className="text-sm">{item.check}: {item.value}</span>
                      </div>
                    ))}
                    {((audit as any).results as any).technical.issues?.map((item: any) => (
                      <div key={item.check} className="flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-red-600" />
                        <span className="text-sm">{item.check}: {item.value}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {((audit as any).results as any)?.content && (
              <Card>
                <CardHeader>
                  <CardTitle>Content Quality (E-E-A-T)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground">E-E-A-T Score</p>
                    <p className="text-3xl font-bold">
                      {((audit as any).results as any).content.eeat_score || 0}/100
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {((audit as any).results as any)?.schema && (
              <Card>
                <CardHeader>
                  <CardTitle>Schema Markup</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm mb-2">
                    {((audit as any).results as any).schema.schemas?.length || 0} schema types detected
                  </p>
                  {((audit as any).results as any).schema.schemas?.map((schema: any) => (
                    <Badge key={schema.type} variant="secondary" className="mr-2">
                      {schema.type}
                    </Badge>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Error State */}
        {audit.status === "failed" && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Audit Failed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <AlertCircle className="h-5 w-5 text-destructive" />
                <div>
                  <p className="font-medium">An error occurred during the audit.</p>
                  <p className="text-sm text-muted-foreground">
                    {(audit as any).error_message || "Please try again or contact support."}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
