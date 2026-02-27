"use client";

import { useEffect, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getCreditRequests, submitPaymentProof, CreditRequestResponse } from "@/lib/api";
import { logger, LogContext } from "@/lib/logger";
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft,
  Loader2,
  Clock,
  CheckCircle,
  XCircle,
  Upload,
  FileText,
  DollarSign
} from "lucide-react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const statusConfig = {
  pending: { icon: Clock, color: "bg-yellow-500", label: "Pending" },
  invoice_sent: { icon: FileText, color: "bg-blue-500", label: "Invoice Sent" },
  proof_uploaded: { icon: Upload, color: "bg-purple-500", label: "Proof Uploaded" },
  approved: { icon: CheckCircle, color: "bg-green-500", label: "Approved" },
  rejected: { icon: XCircle, color: "bg-red-500", label: "Rejected" },
};

export default function CreditRequestsPage() {
  const [requests, setRequests] = useState<CreditRequestResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isPending, startTransition] = useTransition();
  const [uploadDialogOpen, setUploadDialogOpen] = useState<string | null>(null);
  const [proofUrl, setProofUrl] = useState("");
  const [proofNotes, setProofNotes] = useState("");

  const fetchRequests = async () => {
    try {
      const data = await getCreditRequests(50, 0);
      setRequests(data.requests || []);
      setTotal(data.total || 0);
    } catch (err) {
      logger.error(LogContext.CREDITS, err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    startTransition(() => fetchRequests());
  }, []);

  const handleUploadProof = async (requestId: string) => {
    if (!proofUrl) return;

    startTransition(async () => {
      try {
        await submitPaymentProof(requestId, {
          proof_url: proofUrl,
          notes: proofNotes || undefined,
        });
        setUploadDialogOpen(null);
        setProofUrl("");
        setProofNotes("");
        await fetchRequests();
      } catch (err) {
        logger.error(LogContext.CREDITS, err);
        alert(err instanceof Error ? err.message : "Failed to submit proof");
      }
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-4xl">
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 rounded-lg bg-muted" />
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
            <Link href="/credits">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Credits
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Credit Requests</h1>
          </div>
          <Link href="/credits">
            <Button>Request Credits</Button>
          </Link>
        </div>

        {requests.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <DollarSign className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No credit requests yet</h3>
              <p className="mt-2 text-muted-foreground">
                Request credits to start analyzing websites
              </p>
              <Link href="/credits">
                <Button className="mt-4">Request Credits</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {requests.map((request) => {
              const config = statusConfig[request.status];
              const StatusIcon = config.icon;

              return (
                <Card key={request.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">
                        {request.credits_requested} Credits
                      </CardTitle>
                      <Badge className={`${config.color} text-white`}>
                        <StatusIcon className="mr-1 h-3 w-3" />
                        {config.label}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Invoice:</span>
                        <span className="font-mono">{request.invoice_number || "Pending"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Amount:</span>
                        <span>${request.amount} {request.currency}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Created:</span>
                        <span>{formatDate(request.created_at)}</span>
                      </div>
                      {request.payment_notes && (
                        <div className="mt-2 rounded bg-muted p-2">
                          <p className="text-muted-foreground">Notes: {request.payment_notes}</p>
                        </div>
                      )}
                      {request.admin_notes && (
                        <div className="mt-2 rounded bg-muted p-2">
                          <p className="text-muted-foreground">Admin: {request.admin_notes}</p>
                        </div>
                      )}
                    </div>

                    {(request.status === "pending" || request.status === "invoice_sent") && (
                      <div className="mt-4">
                        <Dialog
                          open={uploadDialogOpen === request.id}
                          onOpenChange={(open) => {
                            setUploadDialogOpen(open ? request.id : null);
                            if (!open) {
                              setProofUrl("");
                              setProofNotes("");
                            }
                          }}
                        >
                          <DialogTrigger asChild>
                            <Button variant="outline" className="w-full">
                              <Upload className="mr-2 h-4 w-4" />
                              Upload Payment Proof
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Upload Payment Proof</DialogTitle>
                              <DialogDescription>
                                Provide a URL to your payment confirmation (receipt, screenshot, etc.)
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="space-y-2">
                                <Label htmlFor="proof-url">Proof URL</Label>
                                <Input
                                  id="proof-url"
                                  type="url"
                                  placeholder="https://..."
                                  value={proofUrl}
                                  onChange={(e) => setProofUrl(e.target.value)}
                                />
                              </div>
                              <div className="space-y-2">
                                <Label htmlFor="proof-notes">Notes (Optional)</Label>
                                <Textarea
                                  id="proof-notes"
                                  placeholder="Payment reference, date, etc."
                                  value={proofNotes}
                                  onChange={(e) => setProofNotes(e.target.value)}
                                />
                              </div>
                              <Button
                                className="w-full"
                                onClick={() => handleUploadProof(request.id)}
                                disabled={!proofUrl || isPending}
                              >
                                {isPending ? (
                                  <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Submitting...
                                  </>
                                ) : (
                                  "Submit Proof"
                                )}
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
