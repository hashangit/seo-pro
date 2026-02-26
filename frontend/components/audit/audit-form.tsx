"use client";

import { useState, useTransition, useOptimistic } from "react";
import { useRouter } from "next/navigation";
import { estimateAudit, runAudit } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

type OptimisticState = {
  isEstimating: boolean;
  isRunning: boolean;
  estimatedCredits: number | null;
};

export function AuditForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [estimate, setEstimate] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isEstimatePending, startEstimateTransition] = useTransition();
  const [isRunPending, startRunTransition] = useTransition();

  // Optimistic state for showing immediate feedback
  const [optimisticState, setOptimisticState] = useOptimistic<OptimisticState>({
    isEstimating: false,
    isRunning: false,
    estimatedCredits: null,
  });

  const handleEstimate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setEstimate(null);

    startEstimateTransition(async () => {
      setOptimisticState({ isEstimating: true, isRunning: false, estimatedCredits: null });
      try {
        const result = await estimateAudit({ url });
        setEstimate(result);
        setOptimisticState({ isEstimating: false, isRunning: false, estimatedCredits: result.credits_required });
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to get estimate");
        setOptimisticState({ isEstimating: false, isRunning: false, estimatedCredits: null });
      }
    });
  };

  const handleRunAudit = async () => {
    if (!estimate) return;
    setError(null);

    startRunTransition(async () => {
      setOptimisticState({ isEstimating: false, isRunning: true, estimatedCredits: estimate.credits_required });
      try {
        const result = await runAudit(estimate.quote_id);
        router.push(`/audit/${result.audit_id}`);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to start audit");
        setOptimisticState({ isEstimating: false, isRunning: false, estimatedCredits: estimate.credits_required });
      }
    });
  };

  const isEstimating = isEstimatePending || optimisticState.isEstimating;
  const isRunning = isRunPending || optimisticState.isRunning;
  const isDisabled = isEstimating || isRunning;

  return (
    <Card className="mx-auto max-w-2xl">
      <CardHeader>
        <CardTitle>SEO Site Audit</CardTitle>
        <CardDescription>
          Get a comprehensive SEO analysis for your website. See the cost before you commit.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleEstimate} className="space-y-6">
          {/* URL Input */}
          <div>
            <label className="mb-2 block text-sm font-medium">
              Website URL
            </label>
            <div className="flex gap-2">
              <Input
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isDisabled}
                required
                className="flex-1"
              />
              <Button
                type="submit"
                disabled={isDisabled || !url}
                variant="secondary"
              >
                {isEstimating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Estimating...
                  </>
                ) : (
                  "Get Estimate"
                )}
              </Button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {/* Estimate Results */}
          {(estimate || isEstimating) && (
            <div className="space-y-4 rounded-lg border bg-muted/50 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Cost Estimate</h3>
                {isEstimating ? (
                  <Badge variant="secondary" className="animate-pulse">
                    Calculating...
                  </Badge>
                ) : (
                  <Badge variant="secondary">
                    {estimate?.estimated_pages} pages
                  </Badge>
                )}
              </div>

              {isEstimating ? (
                <div className="animate-pulse space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="h-16 rounded bg-muted" />
                    <div className="h-16 rounded bg-muted" />
                  </div>
                  <div className="h-12 rounded bg-muted" />
                </div>
              ) : estimate && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Credits Required</p>
                      <p className="text-2xl font-bold">
                        {estimate.credits_required}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Cost (USD)</p>
                      <p className="text-2xl font-bold">
                        ${estimate.cost_usd}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-md bg-background p-3">
                    <p className="whitespace-pre-line text-sm">{estimate.breakdown}</p>
                  </div>

                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <p>Quote expires in 30 minutes</p>
                    <p>1 credit = $1 USD</p>
                  </div>

                  <Button
                    onClick={handleRunAudit}
                    disabled={isRunning}
                    className="w-full"
                    size="lg"
                  >
                    {isRunning ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Starting Audit...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Confirm & Run Analysis ({estimate.credits_required} credits)
                      </>
                    )}
                  </Button>
                </>
              )}
            </div>
          )}

          {/* Pricing Info */}
          {!estimate && !isEstimating && (
            <div className="rounded-lg border bg-muted/30 p-4 text-sm">
              <p className="font-medium">Credit-Based Pricing</p>
              <ul className="mt-2 space-y-1 text-muted-foreground">
                <li>• 1 page = 7 credits ($0.875)</li>
                <li>• Full page audit (12 analyses) = 8 credits ($1.00)</li>
                <li>• Individual analysis = 1 credit ($0.125)</li>
              </ul>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
