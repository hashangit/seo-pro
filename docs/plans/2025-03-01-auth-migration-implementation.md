# Auth Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate from @workos-inc/authkit-react to @workos-inc/authkit-nextjs to fix 401 authentication errors.

**Architecture:** Server-first authentication with HttpOnly cookies. Server components use `withAuth()` and `getAccessToken()` for API calls. Client components use server actions for mutations. Tokens never exposed to client-side JavaScript.

**Tech Stack:** Next.js 15, @workos-inc/authkit-nextjs, TypeScript, FastAPI backend

---

## Phase 1: Package Migration

### Task 1: Install New SDK and Remove Old SDK

**Files:**
- Modify: `frontend/package.json`

**Step 1: Remove old SDK and install new SDK**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
pnpm remove @workos-inc/authkit-react
pnpm add @workos-inc/authkit-nextjs
```

**Step 2: Verify installation**

```bash
pnpm list @workos-inc/authkit-nextjs
```

Expected: Shows `@workos-inc/authkit-nextjs x.x.x`

**Step 3: Commit**

```bash
git add package.json pnpm-lock.yaml
git commit -m "chore: replace authkit-react with authkit-nextjs

- Remove @workos-inc/authkit-react
- Add @workos-inc/authkit-nextjs for Next.js 15 App Router support

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Update Environment Variables

**Files:**
- Modify: `frontend/.env.example`
- Create: `frontend/.env.local` (if not exists, for local dev)

**Step 1: Update .env.example with new variables**

Add to `frontend/.env.example`:

```env
# WorkOS AuthKit Next.js Configuration
# Server-side only (never expose to client)
WORKOS_API_KEY=your-workos-api-key-here
WORKOS_CLIENT_ID=client_xxxxxxxxxxxxxxxxxxxxxxxx
WORKOS_COOKIE_PASSWORD=generate-with-openssl-rand-base64-32

# Client-accessible
NEXT_PUBLIC_WORKOS_REDIRECT_URI=http://localhost:3000/callback
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8080
```

**Step 2: Generate cookie password for local dev**

```bash
openssl rand -base64 32
```

**Step 3: Create/update .env.local with actual values**

Create or update `frontend/.env.local` with your actual WorkOS credentials:

```env
WORKOS_API_KEY=<your-actual-api-key>
WORKOS_CLIENT_ID=<your-actual-client-id>
WORKOS_COOKIE_PASSWORD=<generated-32-char-password>
NEXT_PUBLIC_WORKOS_REDIRECT_URI=http://localhost:3000/callback
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8080
```

**Step 4: Commit .env.example only (NOT .env.local)**

```bash
git add frontend/.env.example
git commit -m "chore: update env example for authkit-nextjs

Add WORKOS_COOKIE_PASSWORD and reorganize variables
for authkit-nextjs compatibility.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Core Infrastructure

### Task 3: Create Middleware for Route Protection

**Files:**
- Create: `frontend/middleware.ts`

**Step 1: Create middleware.ts**

Create `frontend/middleware.ts`:

```typescript
import { authkitMiddleware } from '@workos-inc/authkit-nextjs';

export default authkitMiddleware({
  middlewareAuth: {
    enabled: true,
    unauthenticatedPaths: [
      '/',
      '/login',
      '/signup',
      '/callback',
      '/api/auth/:path*',
    ],
  },
});

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/settings/:path*',
    '/audits/:path*',
    '/admin/:path*',
  ],
};
```

**Step 2: Verify no TypeScript errors**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
pnpm tsc --noEmit
```

Expected: No errors related to middleware

**Step 3: Commit**

```bash
git add frontend/middleware.ts
git commit -m "feat: add authkit middleware for route protection

Configures authkitMiddleware to protect dashboard, settings,
audits, and admin routes. Public routes remain accessible.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Create Callback Route Handler

**Files:**
- Create: `frontend/app/callback/route.ts`

**Step 1: Create callback route**

Create `frontend/app/callback/route.ts`:

```typescript
import { handleAuth } from '@workos-inc/authkit-nextjs';

export const GET = handleAuth();
```

**Step 2: Commit**

```bash
git add frontend/app/callback/route.ts
git commit -m "feat: add WorkOS callback route handler

Uses handleAuth() for automatic OAuth callback processing.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Create Login Route Handler

**Files:**
- Create: `frontend/app/login/route.ts`

**Step 1: Create login route**

Create `frontend/app/login/route.ts`:

```typescript
import { getSignInUrl } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export async function GET() {
  const signInUrl = await getSignInUrl();
  redirect(signInUrl);
}
```

**Step 2: Commit**

```bash
git add frontend/app/login/route.ts
git commit -m "feat: add login route handler

Redirects users to WorkOS hosted sign-in page.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Update Root Layout with AuthKitProvider

**Files:**
- Modify: `frontend/app/layout.tsx`

**Step 1: Read current layout.tsx**

```bash
cat frontend/app/layout.tsx
```

**Step 2: Update layout.tsx to use AuthKitProvider from authkit-nextjs**

Replace the import and wrap children with AuthKitProvider. The file should look like:

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AuthKitProvider } from '@workos-inc/authkit-nextjs/components';
import { Toaster } from '@/components/ui/toaster';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'SEO Pro',
  description: 'Professional SEO Analysis Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthKitProvider>
          {children}
          <Toaster />
        </AuthKitProvider>
      </body>
    </html>
  );
}
```

**Step 3: Verify no TypeScript errors**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
pnpm tsc --noEmit
```

**Step 4: Commit**

```bash
git add frontend/app/layout.tsx
git commit -m "feat: update layout with authkit-nextjs provider

Replace authkit-react provider with authkit-nextjs
AuthKitProvider in root layout.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: API Layer

### Task 7: Create Server-Side API Client

**Files:**
- Create: `frontend/lib/api-client.ts`

**Step 1: Create API client**

Create `frontend/lib/api-client.ts`:

```typescript
import { getAccessToken } from '@workos-inc/authkit-nextjs';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAccessToken();

  if (!token) {
    throw new ApiError(401, 'Unauthorized: No session');
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (response.status === 401) {
    throw new ApiError(401, 'Unauthorized: Session expired');
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      response.status,
      `API Error: ${response.status} - ${errorText}`
    );
  }

  return response.json();
}

// Typed response interfaces
export interface CreditBalanceResponse {
  balance: number;
}

export interface AuditListResponse {
  audits: Array<{
    id: string;
    url: string;
    status: string;
    created_at: string;
    completed_at: string | null;
  }>;
  total: number;
}

export interface CreditRequest {
  id: string;
  user_id: string;
  amount: number;
  status: string;
  created_at: string;
}

// Credit API functions
export async function getCreditBalance(): Promise<CreditBalanceResponse> {
  return apiRequest<CreditBalanceResponse>('/api/v1/credits/balance');
}

export async function useCredits(
  amount: number,
  reason: string
): Promise<{ success: boolean; newBalance: number }> {
  return apiRequest<{ success: boolean; newBalance: number }>(
    '/api/v1/credits/use',
    {
      method: 'POST',
      body: JSON.stringify({ amount, reason }),
    }
  );
}

// Audit API functions
export async function listAudits(
  limit: number = 100,
  offset: number = 0
): Promise<AuditListResponse> {
  return apiRequest<AuditListResponse>(
    `/api/v1/audits?limit=${limit}&offset=${offset}`
  );
}

export async function getAudit(id: string): Promise<{ audit: AuditListResponse['audits'][0] }> {
  return apiRequest<{ audit: AuditListResponse['audits'][0] }>(
    `/api/v1/audits/${id}`
  );
}

// Admin API functions
export async function adminGetCreditRequests(
  status?: string,
  limit: number = 50,
  offset: number = 0
): Promise<{ requests: CreditRequest[]; total: number }> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (status) {
    params.append('status', status);
  }
  return apiRequest<{ requests: CreditRequest[]; total: number }>(
    `/api/v1/admin/credit-requests?${params}`
  );
}

export async function adminApproveCreditRequest(
  requestId: string
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(
    `/api/v1/admin/credit-requests/${requestId}/approve`,
    { method: 'POST' }
  );
}
```

**Step 2: Verify no TypeScript errors**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
pnpm tsc --noEmit
```

**Step 3: Commit**

```bash
git add frontend/lib/api-client.ts
git commit -m "feat: add server-side API client with token injection

Provides typed API functions that automatically inject
access tokens from authkit-nextjs session.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Create Auth Server Actions

**Files:**
- Create: `frontend/actions/auth.ts`

**Step 1: Create auth actions**

Create `frontend/actions/auth.ts`:

```typescript
'use server';

import { signOut } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export async function signOutAction() {
  await signOut();
  redirect('/');
}
```

**Step 2: Commit**

```bash
mkdir -p frontend/actions
git add frontend/actions/auth.ts
git commit -m "feat: add sign out server action

Provides server action for signing out users.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Create Credits Server Actions

**Files:**
- Create: `frontend/actions/credits.ts`

**Step 1: Create credits actions**

Create `frontend/actions/credits.ts`:

```typescript
'use server';

import { getAccessToken } from '@workos-inc/authkit-nextjs';
import { revalidatePath } from 'next/cache';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function purchaseCredits(amount: number) {
  const token = await getAccessToken();

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(`${API_URL}/api/v1/credits/purchase`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ amount }),
  });

  if (!response.ok) {
    throw new Error('Failed to purchase credits');
  }

  revalidatePath('/dashboard');
  revalidatePath('/settings/credits');
  return response.json();
}

export async function requestCredits(amount: number, reason: string) {
  const token = await getAccessToken();

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(`${API_URL}/api/v1/credits/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ amount, reason }),
  });

  if (!response.ok) {
    throw new Error('Failed to request credits');
  }

  revalidatePath('/settings/credits');
  return response.json();
}
```

**Step 2: Commit**

```bash
git add frontend/actions/credits.ts
git commit -m "feat: add credits server actions

Provides server actions for purchasing and requesting credits
with automatic token injection and cache revalidation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Create Client Auth Hook

**Files:**
- Create: `frontend/hooks/use-auth.ts`

**Step 1: Create auth hook**

Create `frontend/hooks/use-auth.ts`:

```typescript
'use client';

import { useAuth } from '@workos-inc/authkit-nextjs';

export interface AuthUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

export function useAuthUser() {
  const { user, loading, getAccessToken } = useAuth();

  return {
    user: user as AuthUser | null,
    loading,
    isAuthenticated: !!user,
    getAccessToken,
  };
}
```

**Step 2: Commit**

```bash
mkdir -p frontend/hooks
git add frontend/hooks/use-auth.ts
git commit -m "feat: add client auth hook wrapper

Provides typed useAuthUser hook for client components
that need auth state.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 4: Component Migration

### Task 11: Update Auth Button Component

**Files:**
- Modify: `frontend/components/auth/auth-button.tsx`

**Step 1: Read current auth-button.tsx**

```bash
cat frontend/components/auth/auth-button.tsx
```

**Step 2: Update to use new auth hook**

Update `frontend/components/auth/auth-button.tsx`:

```typescript
'use client';

import { useAuthUser } from '@/hooks/use-auth';
import { signOutAction } from '@/actions/auth';
import { Button } from '@/components/ui/button';

export function AuthButton() {
  const { user, loading, isAuthenticated } = useAuthUser();

  if (loading) {
    return (
      <Button variant="ghost" disabled>
        Loading...
      </Button>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <Button variant="default" asChild>
        <a href="/login">Sign In</a>
      </Button>
    );
  }

  return (
    <form action={signOutAction}>
      <Button variant="outline" type="submit">
        Sign Out ({user.firstName || user.email})
      </Button>
    </form>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/components/auth/auth-button.tsx
git commit -m "feat: update auth button to use new auth hook

Migrates auth-button to use useAuthUser hook and
signOutAction server action.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 12: Update Dashboard Page to Server Component

**Files:**
- Modify: `frontend/app/dashboard/page.tsx`

**Step 1: Read current dashboard page**

```bash
cat frontend/app/dashboard/page.tsx
```

**Step 2: Convert to server component with withAuth**

Update `frontend/app/dashboard/page.tsx` to be a server component:

```typescript
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
        firstName: user.firstName,
        email: user.email,
      }}
      creditBalance={credits.balance}
      recentAudits={audits.audits}
    />
  );
}
```

**Step 3: Create dashboard content client component (if interactivity needed)**

Create `frontend/app/dashboard/dashboard-content.tsx` for any client-side interactivity:

```typescript
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
    <div className="space-y-6">
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

      {/* Add more dashboard content here */}
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/app/dashboard/
git commit -m "feat: convert dashboard to server component

Uses withAuth for authentication and fetches data server-side
with automatic token injection.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 13: Update Audits Page to Server Component

**Files:**
- Modify: `frontend/app/audits/page.tsx`

**Step 1: Read current audits page**

```bash
cat frontend/app/audits/page.tsx
```

**Step 2: Convert to server component**

Update `frontend/app/audits/page.tsx`:

```typescript
import { withAuth } from '@workos-inc/authkit-nextjs';
import { listAudits } from '@/lib/api-client';
import { AuditsTable } from './audits-table';

interface AuditsPageProps {
  searchParams: Promise<{
    page?: string;
  }>;
}

export default async function AuditsPage({ searchParams }: AuditsPageProps) {
  const { user } = await withAuth({ ensureSignedIn: true });
  const params = await searchParams;

  const page = parseInt(params.page || '1', 10);
  const limit = 20;
  const offset = (page - 1) * limit;

  const { audits, total } = await listAudits(limit, offset);
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audits</h1>
        <p className="text-muted-foreground">
          {total.toLocaleString()} total audits
        </p>
      </div>

      <AuditsTable audits={audits} />

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          {/* Add pagination component here */}
        </div>
      )}
    </div>
  );
}
```

**Step 3: Create audits table client component**

Create `frontend/app/audits/audits-table.tsx`:

```typescript
'use client';

import { useState } from 'react';
import Link from 'next/link';

interface Audit {
  id: string;
  url: string;
  status: string;
  created_at: string;
  completed_at: string | null;
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

      <div className="rounded-lg border">
        <table className="w-full">
          <thead className="bg-muted">
            <tr>
              <th className="px-4 py-2 text-left">URL</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Created</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAudits.map((audit) => (
              <tr key={audit.id} className="border-t">
                <td className="px-4 py-2">{audit.url}</td>
                <td className="px-4 py-2">{audit.status}</td>
                <td className="px-4 py-2">
                  {new Date(audit.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-2">
                  <Link
                    href={`/audits/${audit.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/app/audits/
git commit -m "feat: convert audits page to server component

Uses withAuth for authentication and fetches audit data
server-side with automatic token injection.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 14: Update Admin Credit Requests Page

**Files:**
- Modify: `frontend/app/admin/credits/page.tsx`

**Step 1: Read current admin credits page**

```bash
cat frontend/app/admin/credits/page.tsx
```

**Step 2: Convert to server component**

Update `frontend/app/admin/credits/page.tsx`:

```typescript
import { withAuth } from '@workos-inc/authkit-nextjs';
import { adminGetCreditRequests } from '@/lib/api-client';
import { CreditRequestsTable } from './credit-requests-table';

interface AdminCreditsPageProps {
  searchParams: Promise<{
    status?: string;
    page?: string;
  }>;
}

export default async function AdminCreditsPage({
  searchParams,
}: AdminCreditsPageProps) {
  const { user } = await withAuth({ ensureSignedIn: true });
  const params = await searchParams;

  const page = parseInt(params.page || '1', 10);
  const limit = 50;
  const offset = (page - 1) * limit;

  const { requests, total } = await adminGetCreditRequests(
    params.status,
    limit,
    offset
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Credit Requests</h1>
        <p className="text-muted-foreground">
          {total.toLocaleString()} total requests
        </p>
      </div>

      <CreditRequestsTable requests={requests} />
    </div>
  );
}
```

**Step 3: Create credit requests table with actions**

Create `frontend/app/admin/credits/credit-requests-table.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { approveCreditRequest } from './actions';

interface CreditRequest {
  id: string;
  user_id: string;
  amount: number;
  status: string;
  created_at: string;
}

interface CreditRequestsTableProps {
  requests: CreditRequest[];
}

export function CreditRequestsTable({ requests }: CreditRequestsTableProps) {
  const [processingId, setProcessingId] = useState<string | null>(null);

  const handleApprove = async (requestId: string) => {
    setProcessingId(requestId);
    try {
      await approveCreditRequest(requestId);
      // Refresh the page to show updated data
      window.location.reload();
    } catch (error) {
      console.error('Failed to approve request:', error);
      alert('Failed to approve request');
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="rounded-lg border">
      <table className="w-full">
        <thead className="bg-muted">
          <tr>
            <th className="px-4 py-2 text-left">User ID</th>
            <th className="px-4 py-2 text-left">Amount</th>
            <th className="px-4 py-2 text-left">Status</th>
            <th className="px-4 py-2 text-left">Created</th>
            <th className="px-4 py-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {requests.map((request) => (
            <tr key={request.id} className="border-t">
              <td className="px-4 py-2 font-mono text-sm">
                {request.user_id.slice(0, 8)}...
              </td>
              <td className="px-4 py-2">{request.amount.toLocaleString()}</td>
              <td className="px-4 py-2">{request.status}</td>
              <td className="px-4 py-2">
                {new Date(request.created_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-2">
                {request.status === 'pending' && (
                  <button
                    onClick={() => handleApprove(request.id)}
                    disabled={processingId === request.id}
                    className="rounded bg-green-600 px-3 py-1 text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    {processingId === request.id ? 'Processing...' : 'Approve'}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Step 4: Create approve action**

Create `frontend/app/admin/credits/actions.ts`:

```typescript
'use server';

import { getAccessToken } from '@workos-inc/authkit-nextjs';
import { revalidatePath } from 'next/cache';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function approveCreditRequest(requestId: string) {
  const token = await getAccessToken();

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(
    `${API_URL}/api/v1/admin/credit-requests/${requestId}/approve`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error('Failed to approve credit request');
  }

  revalidatePath('/admin/credits');
  return response.json();
}
```

**Step 5: Commit**

```bash
git add frontend/app/admin/credits/
git commit -m "feat: convert admin credits page to server component

Uses withAuth for authentication and server actions for
credit request approval with automatic token injection.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 5: Cleanup

### Task 15: Delete Old Auth Files

**Files:**
- Delete: `frontend/app/auth/callback/page.tsx`
- Delete: `frontend/lib/auth.tsx`
- Delete: `frontend/app/providers.tsx`
- Delete: `frontend/components/providers.tsx`

**Step 1: Delete old callback page**

```bash
rm -rf frontend/app/auth/callback/
```

**Step 2: Delete old auth utilities**

```bash
rm frontend/lib/auth.tsx
```

**Step 3: Delete old providers**

```bash
rm frontend/app/providers.tsx
rm frontend/components/providers.tsx
```

**Step 4: Verify no broken imports**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
pnpm tsc --noEmit
```

Expected: No errors

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove old auth files

Delete auth callback page, old auth utilities, and providers
that are replaced by authkit-nextjs.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 16: Update Imports Across Codebase

**Files:**
- Any files importing from `@workos-inc/authkit-react`

**Step 1: Find remaining old imports**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
grep -r "@workos-inc/authkit-react" --include="*.tsx" --include="*.ts" .
```

**Step 2: Update each file to use new imports**

For each file found:
- Change `import { useAuth } from '@workos-inc/authkit-react'`
- To `import { useAuthUser } from '@/hooks/use-auth'` (for client components)
- Or convert to server component using `withAuth` from `@workos-inc/authkit-nextjs`

**Step 3: Verify no TypeScript errors**

```bash
pnpm tsc --noEmit
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: update all auth imports to authkit-nextjs

Replace all authkit-react imports with authkit-nextjs
or the new useAuthUser hook.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 6: Testing

### Task 17: Test Sign-In Flow

**Step 1: Start development server**

```bash
cd /Users/hashanw/Developer/seo-pro/frontend
pnpm dev
```

**Step 2: Navigate to login**

1. Open http://localhost:3000
2. Click "Sign In" button
3. Verify redirect to WorkOS hosted login

**Step 3: Complete sign-in**

1. Enter credentials in WorkOS login
2. Verify redirect back to /callback
3. Verify redirect to dashboard

**Step 4: Verify session**

1. Check that user data is displayed
2. Refresh page and verify session persists

---

### Task 18: Test Protected Routes

**Step 1: Test unauthenticated access**

1. Sign out
2. Navigate to /dashboard
3. Verify redirect to login

**Step 2: Test authenticated access**

1. Sign in
2. Navigate to /dashboard
3. Verify page loads with user data

---

### Task 19: Test API Calls

**Step 1: Test credit balance API**

1. Sign in
2. Navigate to /dashboard
3. Verify credit balance is displayed

**Step 2: Test audits API**

1. Sign in
2. Navigate to /audits
3. Verify audits list is displayed

**Step 3: Check network requests**

1. Open browser dev tools
2. Verify Authorization header is present in API requests
3. Verify no 401 errors

---

### Task 20: Test Sign-Out Flow

**Step 1: Sign out**

1. Click "Sign Out" button
2. Verify redirect to home page

**Step 2: Verify session cleared**

1. Try to access /dashboard
2. Verify redirect to login

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-2 | Package migration and environment setup |
| 2 | 3-6 | Core infrastructure (middleware, routes, provider) |
| 3 | 7-10 | API layer (client, actions, hooks) |
| 4 | 11-14 | Component migration |
| 5 | 15-16 | Cleanup old files |
| 6 | 17-20 | Testing |

**Total Tasks:** 20
**Estimated Time:** 2-3 hours

---

## References

- [WorkOS AuthKit Next.js Docs](https://workos.com/docs/authkit/nextjs/overview)
- [Design Document](./2025-03-01-auth-migration-design.md)
