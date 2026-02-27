"use client";

import { useEffect, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  adminGetCreditRequests,
  adminApproveCreditRequest,
  adminRejectCreditRequest,
  CreditRequestResponse,
} from "@/lib/api";
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
  RefreshCw,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const statusConfig = {
  pending: { icon: Clock, color: "bg-yellow-500", label: "Pending" },
  invoice_sent: { icon: FileText, color: "bg-blue-500", label: "Invoice Sent" },
  proof_uploaded: { icon: Upload, color: "bg-purple-500", label: "Proof Uploaded" },
  approved: { icon: CheckCircle, color: "bg-green-500", label: "Approved" },
  rejected: { icon: XCircle, color: "bg-red-500", label: "Rejected" },
};

export default function AdminCreditsPage() {
  const [requests, setRequests] = useState<CreditRequestResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isPending, startTransition] = useTransition();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [actionDialogOpen, setActionDialogOpen] = useState<string | null>(null);
  const [adminNotes, setAdminNotes] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const data = await adminGetCreditRequests(
        statusFilter || undefined,
        50,
        0
      );
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
  }, [statusFilter]);

  const handleApprove = async (requestId: string) => {
    startTransition(async () => {
      try {
        await adminApproveCreditRequest(requestId, {
          admin_notes: adminNotes || undefined,
        });
        setActionDialogOpen(null);
        setAdminNotes("");
        await fetchRequests();
      } catch (err) {
        logger.error(LogContext.CREDITS, err);
        alert(err instanceof Error ? err.message : "Failed to approve request");
      }
    });
  };

  const handleReject = async (requestId: string) => {
    if (!rejectReason) {
      alert("Please provide a rejection reason");
      return;
    }

    startTransition(async () => {
      try {
        await adminRejectCreditRequest(requestId, {
          reason: rejectReason,
        });
        setActionDialogOpen(null);
        setRejectReason("");
        await fetchRequests();
      } catch (err) {
        logger.error(LogContext.CREDITS, err);
        alert(err instanceof Error ? err.message : "Failed to reject request");
      }
    });
  };

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Admin: Credit Requests</h1>
          </div>
          <div className="flex items-center gap-4">
            <Select
              value={statusFilter}
              onValueChange={setStatusFilter}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="proof_uploaded">Proof Uploaded</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchRequests()}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{total}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {requests.filter((r) => r.status === "pending").length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Proof Uploaded</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-purple-600">
                {requests.filter((r) => r.status === "proof_uploaded").length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Approved</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-green-600">
                {requests.filter((r) => r.status === "approved").length}
              </p>
            </CardContent>
          </Card>
        </div>

        {loading ? (
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 rounded-lg bg-muted" />
            ))}
          </div>
        ) : requests.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">No credit requests found</p>
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
                      <div className="flex items-center gap-4">
                        <CardTitle className="text-lg">
                          {request.credits_requested} Credits
                        </CardTitle>
                        <Badge className={`${config.color} text-white`}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {config.label}
                        </Badge>
                      </div>
                      <span className="font-mono text-sm text-muted-foreground">
                        {request.invoice_number}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-2 text-sm md:grid-cols-2">
                      <div>
                        <div className="flex justify-between py-1">
                          <span className="text-muted-foreground">User:</span>
                          <span>{(request as any).users?.email || request.user_id}</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-muted-foreground">Amount:</span>
                          <span>${request.amount} {request.currency}</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-muted-foreground">Created:</span>
                          <span>{formatDate(request.created_at)}</span>
                        </div>
                      </div>
                      <div>
                        {request.payment_proof_url && (
                          <div className="py-1">
                            <span className="text-muted-foreground">Proof:</span>
                            <a
                              href={request.payment_proof_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="ml-2 text-blue-600 hover:underline"
                            >
                              View Proof
                            </a>
                          </div>
                        )}
                        {request.payment_notes && (
                          <div className="mt-2 rounded bg-muted p-2">
                            <p className="text-xs text-muted-foreground">
                              User Notes: {request.payment_notes}
                            </p>
                          </div>
                        )}
                        {request.admin_notes && (
                          <div className="mt-2 rounded bg-muted p-2">
                            <p className="text-xs text-muted-foreground">
                              Admin Notes: {request.admin_notes}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {request.status === "proof_uploaded" && (
                      <div className="mt-4 flex gap-2">
                        <Dialog
                          open={actionDialogOpen === `approve-${request.id}`}
                          onOpenChange={(open) => {
                            setActionDialogOpen(open ? `approve-${request.id}` : null);
                            if (!open) setAdminNotes("");
                          }}
                        >
                          <DialogTrigger asChild>
                            <Button className="flex-1">
                              <CheckCircle className="mr-2 h-4 w-4" />
                              Approve
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Approve Credit Request</DialogTitle>
                              <DialogDescription>
                                This will add {request.credits_requested} credits to the user's account.
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="space-y-2">
                                <Label htmlFor="admin-notes">Admin Notes (Optional)</Label>
                                <Textarea
                                  id="admin-notes"
                                  placeholder="Internal notes..."
                                  value={adminNotes}
                                  onChange={(e) => setAdminNotes(e.target.value)}
                                />
                              </div>
                              <Button
                                className="w-full"
                                onClick={() => handleApprove(request.id)}
                                disabled={isPending}
                              >
                                {isPending ? (
                                  <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Approving...
                                  </>
                                ) : (
                                  "Confirm Approval"
                                )}
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>

                        <Dialog
                          open={actionDialogOpen === `reject-${request.id}`}
                          onOpenChange={(open) => {
                            setActionDialogOpen(open ? `reject-${request.id}` : null);
                            if (!open) setRejectReason("");
                          }}
                        >
                          <DialogTrigger asChild>
                            <Button variant="destructive" className="flex-1">
                              <XCircle className="mr-2 h-4 w-4" />
                              Reject
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Reject Credit Request</DialogTitle>
                              <DialogDescription>
                                Please provide a reason for rejection.
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="space-y-2">
                                <Label htmlFor="reject-reason">Rejection Reason *</Label>
                                <Textarea
                                  id="reject-reason"
                                  placeholder="Explain why this request is being rejected..."
                                  value={rejectReason}
                                  onChange={(e) => setRejectReason(e.target.value)}
                                />
                              </div>
                              <Button
                                variant="destructive"
                                className="w-full"
                                onClick={() => handleReject(request.id)}
                                disabled={!rejectReason || isPending}
                              >
                                {isPending ? (
                                  <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Rejecting...
                                  </>
                                ) : (
                                  "Confirm Rejection"
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
