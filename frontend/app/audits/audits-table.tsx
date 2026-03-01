'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';

interface Audit {
  id: string;
  url: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  page_count?: number;
  credits_used?: number;
  error_message?: string | null;
  results?: Record<string, unknown> | null;
}

interface AuditsTableProps {
  audits: Audit[];
}

export function AuditsTable({ audits }: AuditsTableProps) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredAudits = audits.filter((audit) =>
    audit.url.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <input
        type="text"
        placeholder="Search audits..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="w-full rounded-md border px-4 py-2"
      />

      {filteredAudits.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">No audits found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredAudits.map((audit) => (
            <Card key={audit.id}>
              <CardHeader className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{audit.url}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(audit.created_at)}
                  </p>
                </div>
                <Badge
                  variant={
                    audit.status === 'completed'
                      ? 'default'
                      : audit.status === 'failed'
                        ? 'destructive'
                        : 'secondary'
                  }
                >
                  {audit.status}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium">Credits Used</p>
                    <p className="text-2xl font-bold">{audit.credits_used ?? 0}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Pages</p>
                    <p className="text-2xl font-bold">{audit.page_count ?? 0}</p>
                  </div>
                </div>

                {audit.status === 'completed' && audit.results && (
                  <Button variant="outline" size="sm" className="w-full">
                    View Results
                  </Button>
                )}

                {audit.status === 'failed' && audit.error_message && (
                  <p className="text-sm text-destructive mt-2">
                    Error: {audit.error_message}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
