import { withAuth } from '@workos-inc/authkit-nextjs';
import { getCreditBalance, listAudits } from '@/lib/api-client';
import { DashboardContent } from './dashboard-content';

export default async function DashboardPage() {
  const { user } = await withAuth({ ensureSignedIn: true });

  // Fetch data server-side with automatic token injection
  const [credits, audits] = await Promise.all([
    getCreditBalance(),
    listAudits(10, 0),
  ]);

  return (
    <DashboardContent
      user={{
        firstName: user.firstName ?? undefined,
        email: user.email,
      }}
      creditBalance={credits.balance}
      recentAudits={audits.audits}
    />
  );
}
