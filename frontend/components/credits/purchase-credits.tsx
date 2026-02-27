"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CreditCard, Loader2, CheckCircle } from "lucide-react";
import { createCreditRequest, CREDIT_PRICING } from "@/lib/api";
import { logger, LogContext } from "@/lib/logger";
import Link from "next/link";

export function PurchaseCredits() {
  const [credits, setCredits] = useState<number>(64); // Default $8 minimum
  const [notes, setNotes] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ requestId: string; invoiceNumber: string } | null>(null);
  const [isPending, startTransition] = useTransition();

  const amount = credits / CREDIT_PRICING.CREDITS_PER_DOLLAR;
  const isValid = credits >= CREDIT_PRICING.CREDITS_PER_DOLLAR * CREDIT_PRICING.MINIMUM_TOPUP_DOLLARS;

  const handleSubmit = async () => {
    if (!isValid) return;

    setError(null);
    startTransition(async () => {
      try {
        const result = await createCreditRequest({ credits, notes: notes || undefined });
        setSuccess({
          requestId: result.id,
          invoiceNumber: result.invoice_number || "Pending",
        });
      } catch (err) {
        logger.error(LogContext.CREDITS, err);
        setError(err instanceof Error ? err.message : "Failed to create request");
      }
    });
  };

  if (success) {
    return (
      <Card className="mx-auto max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-600">
            <CheckCircle className="h-6 w-6" />
            Request Submitted
          </CardTitle>
          <CardDescription>
            Your credit request has been created
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border bg-muted/50 p-4">
            <div className="mb-2 flex justify-between">
              <span className="text-muted-foreground">Invoice Number:</span>
              <span className="font-mono font-medium">{success.invoiceNumber}</span>
            </div>
            <div className="mb-2 flex justify-between">
              <span className="text-muted-foreground">Credits:</span>
              <span className="font-medium">{credits}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Amount:</span>
              <span className="font-medium">${amount.toFixed(2)} USD</span>
            </div>
          </div>

          <div className="space-y-2 text-sm text-muted-foreground">
            <p><strong>Next steps:</strong></p>
            <ol className="list-inside list-decimal space-y-1">
              <li>Send payment via Wise or bank transfer</li>
              <li>Upload your payment confirmation</li>
              <li>Wait for admin approval</li>
            </ol>
          </div>

          <div className="flex gap-2">
            <Link href="/credits/requests" className="flex-1">
              <Button variant="outline" className="w-full">
                View Requests
              </Button>
            </Link>
            <Button
              onClick={() => setSuccess(null)}
              className="flex-1"
            >
              New Request
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="h-6 w-6" />
          Purchase Credits
        </CardTitle>
        <CardDescription>
          Request credits via manual payment (Wise/Bank Transfer)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <AlertCircle className="h-5 w-5 flex-shrink-0 text-destructive mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="credits">Number of Credits</Label>
          <Input
            id="credits"
            type="number"
            min={64}
            step={8}
            value={credits}
            onChange={(e) => setCredits(parseInt(e.target.value) || 0)}
          />
          <p className="text-xs text-muted-foreground">
            Minimum: 64 credits (${CREDIT_PRICING.MINIMUM_TOPUP_DOLLARS})
          </p>
        </div>

        <div className="rounded-lg border bg-muted/50 p-4">
          <div className="flex justify-between text-sm">
            <span>Credits:</span>
            <span>{credits}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Rate:</span>
            <span>${(1 / CREDIT_PRICING.CREDITS_PER_DOLLAR).toFixed(2)} per credit</span>
          </div>
          <div className="mt-2 flex justify-between border-t pt-2 font-medium">
            <span>Total:</span>
            <span>${amount.toFixed(2)} USD</span>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="notes">Notes (Optional)</Label>
          <Textarea
            id="notes"
            placeholder="Any additional information..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />
        </div>

        {!isValid && (
          <div className="flex items-start gap-3 rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-4">
            <AlertCircle className="h-5 w-5 flex-shrink-0 text-yellow-600 mt-0.5" />
            <p className="text-sm text-yellow-700">
              Minimum purchase is {CREDIT_PRICING.CREDITS_PER_DOLLAR * CREDIT_PRICING.MINIMUM_TOPUP_DOLLARS} credits (${CREDIT_PRICING.MINIMUM_TOPUP_DOLLARS})
            </p>
          </div>
        )}

        <Button
          className="w-full"
          onClick={handleSubmit}
          disabled={!isValid || isPending}
        >
          {isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Request...
            </>
          ) : (
            "Request Credits"
          )}
        </Button>

        <p className="text-center text-xs text-muted-foreground">
          Payment instructions will be provided after submission
        </p>
      </CardContent>
    </Card>
  );
}
