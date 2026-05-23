"use client";

import { useRouter } from "next/navigation";
import {
  ANALYSIS_TYPE_LABELS,
  type AnalysisResult,
} from "@/lib/api";
import { useAnalysesList } from "@/hooks/use-queries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft, ExternalLink, CheckCircle2, AlertCircle, Clock, AlertTriangle } from "lucide-react";

const STATUS_CONFIG = {
  pending: { label: "Pending", color: "secondary", icon: Clock },
  processing: { label: "Processing", color: "default", icon: Loader2 },
  completed: { label: "Completed", color: "success", icon: CheckCircle2 },
  failed: { label: "Failed", color: "destructive", icon: AlertTriangle },
  cancelled: { label: "Cancelled", color: "outline", icon: AlertCircle },
};

export default function AnalysesListPage() {
  const router = useRouter();
  const { data, isLoading, error } = useAnalysesList({ limit: 50 });

  const analyses = data?.analyses || [];
  const total = data?.total || 0;

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Button
        variant="ghost"
        className="mb-6"
        onClick={() => router.push("/")}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      <Card className="mx-auto max-w-4xl">
        <CardHeader>
          <CardTitle>Analysis History</CardTitle>
          <CardDescription>
            {total} analysis{total !== 1 ? "s" : ""} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive mb-4">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm">{error instanceof Error ? error.message : "Failed to load analyses"}</p>
            </div>
          )}

          {analyses.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No analyses yet</p>
              <Button className="mt-4" onClick={() => router.push("/")}>
                Run Your First Analysis
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {analyses.map((analysis: AnalysisResult) => {
                const statusConfig = STATUS_CONFIG[analysis.status];
                const StatusIcon = statusConfig.icon;

                return (
                  <button
                    key={analysis.id}
                    onClick={() => router.push(`/analysis/${analysis.id}`)}
                    className="w-full rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="capitalize">
                            {analysis.analysis_mode.replace("_", " ")}
                          </Badge>
                          <span className="text-sm font-medium truncate">
                            {ANALYSIS_TYPE_LABELS[analysis.analysis_type as keyof typeof ANALYSIS_TYPE_LABELS] || analysis.analysis_type}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground truncate">
                          {analysis.url}
                        </p>
                        <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                          <span>{analysis.credits_used} credits</span>
                          <span>{new Date(analysis.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={statusConfig.color as any}>
                          {statusConfig.icon === Loader2 ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <StatusIcon className="mr-1 h-3 w-3" />
                          )}
                          {statusConfig.label}
                        </Badge>
                        <ExternalLink className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
