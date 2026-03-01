import { withAuth } from '@workos-inc/authkit-nextjs';
import { listAudits } from '@/lib/api-client';
import { AuditsTable } from './audits-table';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface AuditsPageProps {
  searchParams: Promise<{
    page?: string;
    status?: string;
  }>;
}

export default async function AuditsPage({ searchParams }: AuditsPageProps) {
  await withAuth({ ensureSignedIn: true });
  const params = await searchParams;

  const page = parseInt(params.page || '1', 10);
  const limit = 20;
  const offset = (page - 1) * limit;

  const { audits, total } = await listAudits(limit, offset);
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="mb-6 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">Audits</h1>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">
              {total.toLocaleString()} total audits
            </p>
          </div>
        </div>

        <div className="mb-6">
          <Card>
            <CardHeader>
              <CardTitle>Filters</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-4">
              <Link href="/audits">
                <Button variant={params.status ? 'outline' : 'default'} size="sm">
                  All
                </Button>
              </Link>
              <Link href="/audits?status=completed">
                <Button variant={params.status === 'completed' ? 'default' : 'outline'} size="sm">
                  Completed
                </Button>
              </Link>
              <Link href="/audits?status=failed">
                <Button variant={params.status === 'failed' ? 'default' : 'outline'} size="sm">
                  Failed
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {audits.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-muted-foreground">No audits yet. Run an audit to get started!</p>
            </CardContent>
          </Card>
        ) : (
          <AuditsTable audits={audits} />
        )}

        {totalPages > 1 && (
          <div className="flex justify-center gap-2">
            {/* Add pagination component here */}
          </div>
        )}
      </div>
    </div>
  );
}
