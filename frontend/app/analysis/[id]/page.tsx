"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getAnalysisStatus, ANALYSIS_TYPE_LABELS, type AnalysisResult } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft, AlertCircle, CheckCircle2, Clock, AlertTriangle } from "lucide-react";

const STATUS_CONFIG = {
  pending: { label: "Pending", color: "secondary", icon: Clock },
  processing: { label: "Processing", color: "default", icon: Loader2 },
  completed: { label: "Completed", color: "success", icon: CheckCircle2 },
  failed: { label: "Failed", color: "destructive", icon: AlertTriangle },
  cancelled: { label: "Cancelled", color: "outline", icon: AlertCircle },
};

export default function AnalysisResultsPage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params.id as string;

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const result = await getAnalysisStatus(analysisId);
        setAnalysis(result);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load analysis");
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();

    // Poll for updates if processing
    const interval = setInterval(() => {
      if (analysis?.status === "processing" || analysis?.status === "pending") {
        fetchAnalysis();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [analysisId, analysis?.status]);

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="mx-auto max-w-2xl">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p>{error || "Analysis not found"}</p>
            </div>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => router.push("/")}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Home
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[analysis.status];
  const StatusIcon = statusConfig.icon;

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
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>Analysis Results</CardTitle>
              <CardDescription className="mt-1">
                {analysis.url}
              </CardDescription>
            </div>
            <Badge variant={statusConfig.color as any}>
              {statusConfig.icon === Loader2 ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <StatusIcon className="mr-1 h-3 w-3" />
              )}
              {statusConfig.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {/* Analysis Info */}
          <div className="mb-6 grid grid-cols-2 gap-4 rounded-lg bg-muted/50 p-4 sm:grid-cols-4">
            <div>
              <p className="text-sm text-muted-foreground">Type</p>
              <p className="font-medium">
                {ANALYSIS_TYPE_LABELS[analysis.analysis_type as keyof typeof ANALYSIS_TYPE_LABELS] || analysis.analysis_type}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Mode</p>
              <p className="font-medium capitalize">{analysis.analysis_mode.replace("_", " ")}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Credits Used</p>
              <p className="font-medium">{analysis.credits_used}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="font-medium">
                {new Date(analysis.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          {/* Error Message */}
          {analysis.status === "failed" && analysis.error_message && (
            <div className="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <p className="font-medium">Error</p>
              </div>
              <p className="mt-2 text-sm">{analysis.error_message}</p>
            </div>
          )}

          {/* Processing State */}
          {(analysis.status === "pending" || analysis.status === "processing") && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <p className="mt-4 text-lg font-medium">Analysis in progress...</p>
              <p className="text-sm text-muted-foreground">
                This may take a few minutes. Results will appear automatically.
              </p>
            </div>
          )}

          {/* Results */}
          {analysis.status === "completed" && analysis.results_json && (
            <div className="space-y-6">
              {/* Score (if available) */}
              {analysis.results_json.score !== undefined && (
                <div className="text-center">
                  <div className="text-5xl font-bold text-primary">
                    {analysis.results_json.score}
                  </div>
                  <p className="text-sm text-muted-foreground">SEO Score</p>
                </div>
              )}

              {/* Issues */}
              {Array.isArray(analysis.results_json.issues) && analysis.results_json.issues.length > 0 && (
                <div>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    Issues ({analysis.results_json.issues.length})
                  </h3>
                  <ul className="space-y-2">
                    {analysis.results_json.issues.map((issue: any, idx: number) => (
                      <li key={idx} className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
                        <span className="font-medium">{issue.check}</span>
                        {issue.value && <span className="ml-2 text-muted-foreground">- {issue.value}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warnings */}
              {Array.isArray(analysis.results_json.warnings) && analysis.results_json.warnings.length > 0 && (
                <div>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-yellow-600">
                    <AlertTriangle className="h-4 w-4" />
                    Warnings ({analysis.results_json.warnings.length})
                  </h3>
                  <ul className="space-y-2">
                    {analysis.results_json.warnings.map((warning: any, idx: number) => (
                      <li key={idx} className="rounded-lg border border-yellow-300 bg-yellow-50 p-3 text-sm">
                        <span className="font-medium">{warning.check}</span>
                        {warning.value && <span className="ml-2 text-muted-foreground">- {warning.value}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Passes */}
              {Array.isArray(analysis.results_json.passes) && analysis.results_json.passes.length > 0 && (
                <div>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    Passed ({analysis.results_json.passes.length})
                  </h3>
                  <ul className="space-y-2">
                    {analysis.results_json.passes.map((pass: any, idx: number) => (
                      <li key={idx} className="rounded-lg border border-green-300 bg-green-50 p-3 text-sm">
                        <span className="font-medium">{pass.check}</span>
                        {pass.value && <span className="ml-2 text-muted-foreground">- {pass.value}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {Array.isArray(analysis.results_json.recommendations) && analysis.results_json.recommendations.length > 0 && (
                <div>
                  <h3 className="mb-3 font-semibold">Recommendations</h3>
                  <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                    {analysis.results_json.recommendations.map((rec: string, idx: number) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Raw Results (collapsible for debugging) */}
              <details className="mt-6">
                <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                  View raw results
                </summary>
                <pre className="mt-2 overflow-auto rounded-lg bg-muted p-4 text-xs">
                  {JSON.stringify(analysis.results_json, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
