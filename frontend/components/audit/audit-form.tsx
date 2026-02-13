"use client";

import { useState } from "react";
import { estimateAudit, runAudit } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export function AuditForm() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [estimate, setEstimate] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const handleEstimate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setEstimate(null);

    try {
      const result = await estimateAudit({ url });
      setEstimate(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to get estimate");
    } finally {
      setLoading(false);
    }
  };

  const handleRunAudit = async () => {
    if (!estimate) return;

    setRunning(true);
    setError(null);

    try {
      const result = await runAudit(estimate.quote_id);
      router.push(`/audit/${result.audit_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start audit");
      setRunning(false);
    }
  };

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
                disabled={loading || running}
                required
                className="flex-1"
              />
              <Button
                type="submit"
                disabled={loading || !url || running}
                variant="secondary"
              >
                {loading ? (
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
          {estimate && (
            <div className="space-y-4 rounded-lg border bg-muted/50 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Cost Estimate</h3>
                <Badge variant="secondary">
                  {estimate.estimated_pages} pages
                </Badge>
              </div>

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
                disabled={running}
                className="w-full"
                size="lg"
              >
                {running ? (
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
            </div>
          )}

          {/* Pricing Info */}
          {!estimate && (
            <div className="rounded-lg border bg-muted/30 p-4 text-sm">
              <p className="font-medium">Credit-Based Pricing</p>
              <ul className="mt-2 space-y-1 text-muted-foreground">
                <li>• 1 page = 3 credits ($3)</li>
                <li>• Up to 10 pages = 5 credits ($5)</li>
                <li>• Additional 10-page blocks = 2 credits each</li>
              </ul>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
