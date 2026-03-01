'use client';

import { useState } from 'react';
import { approveCreditRequest, rejectCreditRequest } from './actions';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Upload,
  Loader2,
} from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface CreditRequest {
  id: string;
  user_id: string;
  credits_requested: number;
  amount: number;
  currency: string;
  status: string;
  invoice_number: string | null;
  payment_proof_url: string | null;
  payment_notes: string | null;
  admin_notes: string | null;
  created_at: string;
  users?: {
    email: string;
  };
}

interface CreditRequestsTableProps {
  requests: CreditRequest[];
}

const statusConfig = {
  pending: { icon: Clock, color: 'bg-yellow-500', label: 'Pending' },
  invoice_sent: { icon: FileText, color: 'bg-blue-500', label: 'Invoice Sent' },
  proof_uploaded: { icon: Upload, color: 'bg-purple-500', label: 'Proof Uploaded' },
  approved: { icon: CheckCircle, color: 'bg-green-500', label: 'Approved' },
  rejected: { icon: XCircle, color: 'bg-red-500', label: 'Rejected' },
};

export function CreditRequestsTable({ requests }: CreditRequestsTableProps) {
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [actionDialogOpen, setActionDialogOpen] = useState<string | null>(null);
  const [adminNotes, setAdminNotes] = useState('');
  const [rejectReason, setRejectReason] = useState('');

  const handleApprove = async (requestId: string) => {
    setProcessingId(requestId);
    try {
      await approveCreditRequest(requestId, adminNotes || undefined);
      setActionDialogOpen(null);
      setAdminNotes('');
      window.location.reload();
    } catch (error) {
      console.error('Failed to approve request:', error);
      alert(error instanceof Error ? error.message : 'Failed to approve request');
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (requestId: string) => {
    if (!rejectReason) {
      alert('Please provide a rejection reason');
      return;
    }

    setProcessingId(requestId);
    try {
      await rejectCreditRequest(requestId, rejectReason);
      setActionDialogOpen(null);
      setRejectReason('');
      window.location.reload();
    } catch (error) {
      console.error('Failed to reject request:', error);
      alert(error instanceof Error ? error.message : 'Failed to reject request');
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="space-y-4">
      {requests.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No credit requests found</p>
          </CardContent>
        </Card>
      ) : (
        requests.map((request) => {
          const config = statusConfig[request.status as keyof typeof statusConfig] || statusConfig.pending;
          const StatusIcon = config.icon;

          return (
            <Card key={request.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <h3 className="text-lg font-semibold">
                      {request.credits_requested} Credits
                    </h3>
                    <Badge className={`${config.color} text-white`}>
                      <StatusIcon className="mr-1 h-3 w-3" />
                      {config.label}
                    </Badge>
                  </div>
                  {request.invoice_number && (
                    <span className="font-mono text-sm text-muted-foreground">
                      {request.invoice_number}
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 text-sm md:grid-cols-2">
                  <div>
                    <div className="flex justify-between py-1">
                      <span className="text-muted-foreground">User:</span>
                      <span>{request.users?.email || request.user_id}</span>
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

                {request.status === 'proof_uploaded' && (
                  <div className="mt-4 flex gap-2">
                    <Dialog
                      open={actionDialogOpen === `approve-${request.id}`}
                      onOpenChange={(open) => {
                        setActionDialogOpen(open ? `approve-${request.id}` : null);
                        if (!open) setAdminNotes('');
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
                            This will add {request.credits_requested} credits to the user&apos;s account.
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
                            disabled={processingId === request.id}
                          >
                            {processingId === request.id ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Approving...
                              </>
                            ) : (
                              'Confirm Approval'
                            )}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>

                    <Dialog
                      open={actionDialogOpen === `reject-${request.id}`}
                      onOpenChange={(open) => {
                        setActionDialogOpen(open ? `reject-${request.id}` : null);
                        if (!open) setRejectReason('');
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
                            disabled={!rejectReason || processingId === request.id}
                          >
                            {processingId === request.id ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Rejecting...
                              </>
                            ) : (
                              'Confirm Rejection'
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
        })
      )}
    </div>
  );
}
