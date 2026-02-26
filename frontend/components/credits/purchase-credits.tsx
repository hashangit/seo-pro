"use client";

import { AlertCircle, Infinity as InfinityIcon } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/**
 * Purchase Credits Component
 *
 * NOTE: Payment gateway integration removed pending IPG setup.
 * DEV MODE: Users have unlimited access for development.
 *
 * TODO: Integrate a proper IPG (International Payment Gateway) and remove dev mode.
 * When ready, implement the payment flow here.
 */
export function PurchaseCredits() {
  return (
    <Card className="mx-auto max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <InfinityIcon className="h-6 w-6 text-primary" />
          Dev Mode Active
        </CardTitle>
        <CardDescription>
          Unlimited access - Payment gateway integration pending
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Dev Mode Notice */}
        <div className="flex items-start gap-3 rounded-lg border border-primary/50 bg-primary/10 p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-primary mt-0.5" />
          <div className="text-sm">
            <p className="font-medium">Development Mode</p>
            <p className="text-muted-foreground mt-1">
              Payment gateway integration is pending. You have unlimited access to all features
              during development.
            </p>
            <p className="text-xs text-muted-foreground mt-2 italic">
              TODO: Integrate IPG and remove dev mode
            </p>
          </div>
        </div>

        {/* Badge */}
        <div className="flex justify-center">
          <Badge variant="outline" className="text-xs">
            IPG Integration Pending
          </Badge>
        </div>

        <p className="text-center text-xs text-muted-foreground">
          An International Payment Gateway will be integrated soon to handle credit purchases.
        </p>
      </CardContent>
    </Card>
  );
}
