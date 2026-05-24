import { withAuth } from '@workos-inc/authkit-nextjs';
import { listAudits } from '@/lib/api';
import { DashboardContent } from './dashboard-content';

export default async function DashboardPage() {
  const { user, accessToken } = await withAuth({ ensureSignedIn: true });

  const audits = await listAudits(10, 0, accessToken);

  return (
    <DashboardContent
      user={{
        firstName: user.firstName ?? undefined,
        email: user.email,
      }}
      recentAudits={audits.audits}
    />
  );
}
