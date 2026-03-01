'use client';

interface DashboardContentProps {
  user: {
    firstName?: string;
    email: string;
  };
  creditBalance: number;
  recentAudits: Array<{
    id: string;
    url: string;
    status: string;
    created_at: string;
  }>;
}

export function DashboardContent({
  user,
  creditBalance,
  recentAudits,
}: DashboardContentProps) {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold">
            Welcome{user.firstName ? `, ${user.firstName}` : ''}
          </h1>
          <p className="text-muted-foreground">{user.email}</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">Credit Balance</h2>
            <p className="text-3xl font-bold">{creditBalance.toLocaleString()}</p>
          </div>

          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">Recent Audits</h2>
            <p className="text-3xl font-bold">{recentAudits.length}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
