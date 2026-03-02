# Authentication Migration Design: authkit-react to authkit-nextjs

**Date:** 2025-03-01
**Status:** Approved
**Author:** Claude (AI Assistant)
**Reviewers:** Senior Code Reviewer (AI)

---

## Executive Summary

This document describes the migration from `@workos-inc/authkit-react` to `@workos-inc/authkit-nextjs` to fix authentication failures (401 errors) and align with WorkOS's recommended integration pattern for Next.js applications.

### Problem Statement

1. **401 Unauthorized Errors**: API calls from frontend components fail because tokens are not being passed
2. **Wrong SDK**: Using React SDK instead of Next.js SDK limits server-side auth capabilities
3. **Manual Token Management**: Current implementation requires manual token passing which is error-prone
4. **No Server-Side Auth**: Cannot access user data in server components

### Solution

Migrate to `@workos-inc/authkit-nextjs` which provides:
- Automatic token management via HttpOnly cookies
- Server component support with `withAuth()`
- Automatic callback handling with `handleAuth()`
- Middleware-based route protection with `authkitMiddleware()`

---

## Architecture

### Current State (Problematic)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Current Implementation                           │
├─────────────────────────────────────────────────────────────────────┤
│  @workos-inc/authkit-react                                          │
│                                                                     │
│  Client Components ──► useAuth() ──► Token in memory ──► API calls │
│         │                    │              │                       │
│         │                    │              └── ❌ Not passed       │
│         │                    │                                        │
│         └── ❌ No server component support                            │
│                                                                      │
│  Callback: /auth/callback/page.tsx ──► Manual redirect              │
│  Route Protection: None                                             │
│  Token Storage: localStorage/memory (XSS vulnerable)                │
└─────────────────────────────────────────────────────────────────────┘
```

### Target State (Aligned with WorkOS Docs)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Target Implementation                            │
├─────────────────────────────────────────────────────────────────────┤
│  @workos-inc/authkit-nextjs                                         │
│                                                                     │
│  Server Components (PRIMARY)                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  withAuth() ──► getAccessToken() ──► API calls (server-side)│   │
│  │  ✅ Token NEVER exposed to client                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Client Components (for interactivity)                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  useAuth() ──► Server Actions ──► API calls                 │   │
│  │  ✅ Token handled server-side via actions                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Callback: /callback/route.ts ──► handleAuth() (automatic)         │
│  Middleware: middleware.ts ──► authkitMiddleware()                 │
│  Token Storage: HttpOnly cookies (secure)                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Package Migration

**Remove old SDK, install new SDK:**
```bash
pnpm remove @workos-inc/authkit-react
pnpm add @workos-inc/authkit-nextjs
```

### 2. Environment Variables

**Required environment variables (aligned with WorkOS docs):**

```env
# Server-side only (DO NOT expose to client)
WORKOS_API_KEY="your-workos-api-key-here"
WORKOS_CLIENT_ID="client_xxx"
WORKOS_COOKIE_PASSWORD="<32+ character secure random string>"

# Client-accessible
NEXT_PUBLIC_WORKOS_REDIRECT_URI="http://localhost:3000/callback"
NEXT_PUBLIC_APP_URL="http://localhost:3000"
```

**Generate cookie password:**
```bash
openssl rand -base64 32
```

### 3. Middleware Configuration

**File: `frontend/middleware.ts`**

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

**Reference:** [WorkOS Middleware Auth Docs](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/proxy)

### 4. Callback Route Handler

**File: `frontend/app/callback/route.ts`**

```typescript
import { handleAuth } from '@workos-inc/authkit-nextjs';

export const GET = handleAuth();
```

**Reference:** [WorkOS Callback Route Docs](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/callback-route)

### 5. AuthKitProvider in Layout

**File: `frontend/app/layout.tsx`**

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AuthKitProvider } from '@workos-inc/authkit-nextjs/components';
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
        </AuthKitProvider>
      </body>
    </html>
  );
}
```

**Reference:** [WorkOS Provider Docs](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/provider)

### 6. Server-Side API Client

**File: `frontend/lib/api-client.ts`**

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
    throw new ApiError(response.status, `API Error: ${response.status}`);
  }

  return response.json();
}

// Typed API functions
export async function getCreditBalance(): Promise<{ balance: number }> {
  return apiRequest<{ balance: number }>('/api/v1/credits/balance');
}

export async function listAudits(
  limit: number = 100,
  offset: number = 0
): Promise<{ audits: Audit[]; total: number }> {
  return apiRequest<{ audits: Audit[]; total: number }>(
    `/api/v1/audits?limit=${limit}&offset=${offset}`
  );
}

// Add other typed API functions as needed...
```

### 7. Server Component Usage

**File: `frontend/app/dashboard/page.tsx`**

```typescript
import { withAuth } from '@workos-inc/authkit-nextjs';
import { getCreditBalance } from '@/lib/api-client';

export default async function DashboardPage() {
  // ensureSignedIn redirects to login if not authenticated
  const { user } = await withAuth({ ensureSignedIn: true });

  // API call with automatic token injection
  const credits = await getCreditBalance();

  return (
    <div>
      <h1>Welcome, {user.firstName}</h1>
      <p>Credits: {credits.balance}</p>
    </div>
  );
}
```

**Reference:** [WorkOS Server Component Docs](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/access-authentication-data)

### 8. Client Component Hook (for interactivity)

**File: `frontend/hooks/use-auth.ts`**

```typescript
'use client';

import { useAuth } from '@workos-inc/authkit-nextjs';

export function useAuthUser() {
  const { user, loading, getAccessToken } = useAuth();

  return {
    user,
    loading,
    isAuthenticated: !!user,
    getAccessToken,
  };
}
```

### 9. Server Actions for Client-Initiated Mutations

**File: `frontend/actions/credits.ts`**

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
  return response.json();
}
```

### 10. Sign-In Route

**File: `frontend/app/login/route.ts`**

```typescript
import { getSignInUrl } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export async function GET() {
  const signInUrl = await getSignInUrl();
  redirect(signInUrl);
}
```

**Reference:** [WorkOS Sign-In Endpoint Docs](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/sign-in-endpoint)

### 11. Sign-Out Action

**File: `frontend/actions/auth.ts`**

```typescript
'use server';

import { signOut } from '@workos-inc/authkit-nextjs';

export async function signOutAction() {
  await signOut();
}
```

**Reference:** [WorkOS Ending Session Docs](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/ending-the-session)

---

## Files to Modify

### Files to Delete
| File | Reason |
|------|--------|
| `frontend/app/auth/callback/page.tsx` | Replaced by `/callback/route.ts` |
| `frontend/lib/auth.tsx` | Replaced by SDK's built-in auth |
| `frontend/app/providers.tsx` | Provider moves to layout.tsx |
| `frontend/components/providers.tsx` | Provider moves to layout.tsx |

### Files to Create
| File | Purpose |
|------|---------|
| `frontend/middleware.ts` | Route protection with authkitMiddleware |
| `frontend/app/callback/route.ts` | OAuth callback handler |
| `frontend/app/login/route.ts` | Sign-in redirect |
| `frontend/lib/api-client.ts` | Server-side API client with token injection |
| `frontend/actions/credits.ts` | Server actions for credit operations |
| `frontend/actions/auth.ts` | Server actions for auth operations |
| `frontend/hooks/use-auth.ts` | Client-side auth hook wrapper |

### Files to Modify
| File | Changes |
|------|---------|
| `frontend/app/layout.tsx` | Add AuthKitProvider |
| `frontend/app/dashboard/page.tsx` | Use withAuth() + server-side API client |
| `frontend/app/audits/page.tsx` | Convert to server component |
| `frontend/app/admin/*/page.tsx` | Convert to server components |
| `frontend/components/auth/auth-button.tsx` | Use new useAuth hook |
| `frontend/components/credits/credit-balance.tsx` | Use server actions or server component |
| `frontend/package.json` | Replace SDK dependency |
| `frontend/.env.local` | Add new environment variables |

---

## Security Considerations

### Token Handling

| Aspect | Approach | Rationale |
|--------|----------|-----------|
| Storage | HttpOnly cookies | Not accessible via JavaScript (XSS protection) |
| Transmission | Server-side only | Token never exposed to client bundle |
| Refresh | Automatic via SDK | WorkOS handles token refresh |
| Revocation | Via WorkOS dashboard | Session invalidation handled by WorkOS |

### CSRF Protection

The `@workos-inc/authkit-nextjs` SDK handles CSRF protection automatically through:
- SameSite cookie attributes
- State parameter validation in OAuth flow

### Content Security Policy

Recommended CSP headers:
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';
```

---

## Migration Checklist

### Phase 1: Setup
- [ ] Install `@workos-inc/authkit-nextjs`
- [ ] Remove `@workos-inc/authkit-react`
- [ ] Configure environment variables
- [ ] Generate `WORKOS_COOKIE_PASSWORD`

### Phase 2: Core Infrastructure
- [ ] Create `middleware.ts`
- [ ] Create `/callback/route.ts`
- [ ] Create `/login/route.ts`
- [ ] Update `app/layout.tsx` with AuthKitProvider

### Phase 3: API Layer
- [ ] Create `lib/api-client.ts`
- [ ] Create `actions/credits.ts`
- [ ] Create `actions/auth.ts`
- [ ] Create `hooks/use-auth.ts`

### Phase 4: Component Migration
- [ ] Convert dashboard page to server component
- [ ] Convert audits page to server component
- [ ] Convert admin pages to server components
- [ ] Update auth button component
- [ ] Update credit balance component

### Phase 5: Cleanup
- [ ] Delete old callback page
- [ ] Delete old auth utilities
- [ ] Delete old providers
- [ ] Update imports across codebase

### Phase 6: Testing
- [ ] Test sign-in flow
- [ ] Test sign-out flow
- [ ] Test protected routes
- [ ] Test API calls with authentication
- [ ] Test token refresh
- [ ] Test session expiry handling

---

## References

- [WorkOS AuthKit Next.js Overview](https://workos.com/docs/authkit/nextjs/overview)
- [WorkOS Provider Setup](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/provider)
- [WorkOS Middleware/Proxy](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/proxy)
- [WorkOS Callback Route](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/callback-route)
- [WorkOS Access Authentication Data](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/access-authentication-data)
- [WorkOS Protected Routes](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/protected-routes)
- [WorkOS Ending Session](https://workos.com/docs/authkit/nextjs/2-add-authkit-to-your-app/ending-the-session)

---

## Appendix: Backend Compatibility

The FastAPI backend requires **no changes**. It already:
- Validates JWTs using RS256
- Caches JWKS with 15-minute TTL
- Handles token expiry gracefully
- Returns proper 401 responses

The frontend migration only changes how tokens are obtained and passed to the backend.
