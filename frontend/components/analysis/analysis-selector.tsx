"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  estimateAnalysis,
  estimateAudit,
  runAudit,
  ANALYSIS_TYPES,
  ANALYSIS_TYPE_LABELS,
  CREDIT_PRICING,
  type AnalysisType,
} from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle, Zap, FileSearch, Globe } from "lucide-react";

type AnalysisMode = "individual" | "page_audit" | "site_audit";

interface TabConfig {
  id: AnalysisMode;
  label: string;
  icon: React.ReactNode;
  description: string;
  creditInfo: string;
}

const TABS: TabConfig[] = [
  {
    id: "individual",
    label: "Quick Analysis",
    icon: <Zap className="h-4 w-4" />,
    description: "Select specific analysis types to run",
    creditInfo: "1 credit per report",
  },
  {
    id: "page_audit",
    label: "Full Page Audit",
    icon: <FileSearch className="h-4 w-4" />,
    description: "Comprehensive single-page analysis",
    creditInfo: "8 credits (12 types bundled)",
  },
  {
    id: "site_audit",
    label: "Full Site Audit",
    icon: <Globe className="h-4 w-4" />,
    description: "Complete website crawl and analysis",
    creditInfo: "7 credits per page",
  },
];

export function AnalysisSelector() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<AnalysisMode>("individual");
  const [url, setUrl] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<Set<AnalysisType>>(
    new Set(["technical"])
  );
  const [loading, setLoading] = useState(false);
  const [estimate, setEstimate] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const toggleType = useCallback((type: AnalysisType) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
    setEstimate(null);
  }, []);

  const handleEstimate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setEstimate(null);

    try {
      let result;
      if (activeTab === "site_audit") {
        // Use existing audit estimate for site audits
        result = await estimateAudit({ url });
      } else {
        // Use new analysis estimate for individual and page audit
        result = await estimateAnalysis({
          url,
          analysis_mode: activeTab,
          analysis_types: activeTab === "individual" ? Array.from(selectedTypes) : undefined,
        });
      }
      setEstimate(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to get estimate");
    } finally {
      setLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!estimate) return;

    setRunning(true);
    setError(null);

    try {
      if (activeTab === "site_audit") {
        // Site audit uses the existing flow
        const result = await runAudit(estimate.quote_id);
        router.push(`/audit/${result.audit_id}`);
      } else {
        // For individual and page audit, we'll run directly
        // TODO: Implement analysis execution and tracking
        // For now, redirect to a results page
        router.push(`/analysis?mode=${activeTab}&url=${encodeURIComponent(url)}&types=${Array.from(selectedTypes).join(",")}`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setRunning(false);
    }
  };

  const selectedCount = selectedTypes.size;
  const estimatedCredits =
    activeTab === "individual"
      ? selectedCount * CREDIT_PRICING.INDIVIDUAL_REPORT
      : activeTab === "page_audit"
        ? CREDIT_PRICING.PAGE_AUDIT
        : estimate?.credits_required || 0;

  return (
    <Card className="mx-auto max-w-3xl">
      <CardHeader>
        <CardTitle>SEO Analysis</CardTitle>
        <CardDescription>
          Choose your analysis type and get instant SEO insights
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Tab Navigation */}
        <div className="mb-6 flex border-b">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setEstimate(null);
                setError(null);
              }}
              className={`flex flex-1 flex-col items-center gap-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2">
                {tab.icon}
                <span>{tab.label}</span>
              </div>
              <span className="text-xs text-muted-foreground">{tab.creditInfo}</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleEstimate} className="space-y-6">
          {/* URL Input */}
          <div>
            <label className="mb-2 block text-sm font-medium">
              {activeTab === "site_audit" ? "Website URL" : "Page URL"}
            </label>
            <div className="flex gap-2">
              <Input
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setEstimate(null);
                }}
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

          {/* Individual Analysis Type Selection */}
          {activeTab === "individual" && (
            <div>
              <label className="mb-3 block text-sm font-medium">
                Select Analysis Types ({selectedCount} selected)
              </label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {ANALYSIS_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => toggleType(type)}
                    className={`rounded-lg border p-3 text-left text-sm transition-colors ${
                      selectedTypes.has(type)
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border hover:border-primary/50 hover:bg-muted/50"
                    }`}
                  >
                    <div className="font-medium">{ANALYSIS_TYPE_LABELS[type]}</div>
                    <div className="text-xs text-muted-foreground">1 credit</div>
                  </button>
                ))}
              </div>
              {selectedCount === 0 && (
                <p className="mt-2 text-sm text-destructive">
                  Please select at least one analysis type
                </p>
              )}
            </div>
          )}

          {/* Page Audit Info */}
          {activeTab === "page_audit" && (
            <div className="rounded-lg border bg-muted/30 p-4">
              <p className="font-medium">Includes all 12 analysis types:</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {ANALYSIS_TYPES.map((type) => (
                  <Badge key={type} variant="secondary">
                    {ANALYSIS_TYPE_LABELS[type]}
                  </Badge>
                ))}
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                Bundle discount: 12 individual reports would cost 12 credits, bundled at 8 credits (33% off)
              </p>
            </div>
          )}

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
                {estimate.estimated_pages && (
                  <Badge variant="secondary">
                    {estimate.estimated_pages} pages
                  </Badge>
                )}
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
                    ${estimate.cost_usd?.toFixed(2) || (estimate.credits_required / CREDIT_PRICING.CREDITS_PER_DOLLAR).toFixed(2)}
                  </p>
                </div>
              </div>

              {estimate.breakdown && (
                <div className="rounded-md bg-background p-3">
                  <p className="whitespace-pre-line text-sm">{estimate.breakdown}</p>
                </div>
              )}

              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <p>{estimate.quote_id ? "Quote expires in 30 minutes" : "Ready to run"}</p>
                <p>$1 = {CREDIT_PRICING.CREDITS_PER_DOLLAR} credits</p>
              </div>

              <Button
                type="button"
                onClick={handleRunAnalysis}
                disabled={running || (activeTab === "individual" && selectedCount === 0)}
                className="w-full"
                size="lg"
              >
                {running ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting Analysis...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Run Analysis ({estimate.credits_required} credits)
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Pricing Info (when no estimate) */}
          {!estimate && (
            <div className="rounded-lg border bg-muted/30 p-4 text-sm">
              <p className="font-medium">Credit Pricing</p>
              <ul className="mt-2 space-y-1 text-muted-foreground">
                <li>• Individual report: 1 credit ($0.125)</li>
                <li>• Full page audit: {CREDIT_PRICING.PAGE_AUDIT} credits ($1.00) - all 12 types</li>
                <li>• Full site audit: {CREDIT_PRICING.SITE_AUDIT_PER_PAGE} credits per page</li>
                <li>• $1 = {CREDIT_PRICING.CREDITS_PER_DOLLAR} credits | Min. topup: ${CREDIT_PRICING.MINIMUM_TOPUP_DOLLARS}</li>
              </ul>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
