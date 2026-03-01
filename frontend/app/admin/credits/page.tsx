import { withAuth } from '@workos-inc/authkit-nextjs';
import { adminGetCreditRequests } from '@/lib/api-client';
import { CreditRequestsTable } from './credit-requests-table';
import { StatusFilter } from './status-filter';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface AdminCreditsPageProps {
  searchParams: Promise<{
    status?: string;
    page?: string;
  }>;
}

export default async function AdminCreditsPage({
  searchParams,
}: AdminCreditsPageProps) {
  const { user: _user } = await withAuth({ ensureSignedIn: true });
  const params = await searchParams;

  const page = parseInt(params.page || '1', 10);
  const limit = 50;
  const offset = (page - 1) * limit;

  const { requests, total } = await adminGetCreditRequests(
    params.status,
    limit,
    offset
  );

  // Calculate stats
  const pendingCount = requests.filter((r) => r.status === 'pending').length;
  const proofUploadedCount = requests.filter((r) => r.status === 'proof_uploaded').length;
  const approvedCount = requests.filter((r) => r.status === 'approved').length;

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl space-y-6">
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
            <StatusFilter currentStatus={params.status} />
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
              <p className="text-2xl font-bold">{pendingCount}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Proof Uploaded</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-purple-600">{proofUploadedCount}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Approved</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-green-600">{approvedCount}</p>
            </CardContent>
          </Card>
        </div>

        <CreditRequestsTable requests={requests} />
      </div>
    </div>
  );
}
