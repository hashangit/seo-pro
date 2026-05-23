import { withAuth } from '@workos-inc/authkit-nextjs';
import { getCreditBalance, listAudits } from '@/lib/api';
import { DashboardContent } from './dashboard-content';

export default async function DashboardPage() {
  const { user, accessToken } = await withAuth({ ensureSignedIn: true });

  const [credits, audits] = await Promise.all([
    getCreditBalance(accessToken),
    listAudits(10, 0, accessToken),
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
