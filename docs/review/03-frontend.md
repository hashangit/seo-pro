# 03 — Frontend

## Overview

The frontend is a **Next.js 15** application using the **App Router** with **TypeScript**, **Tailwind CSS**, and **shadcn/ui** components. It's deployed on **Vercel** and communicates with the FastAPI gateway.

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/middleware.ts` | ~20 | WorkOS AuthKit middleware wrapping all routes |
| `frontend/lib/api.ts` | ~700 | Client-side API client (takes token param) |
| `frontend/hooks/use-auth.ts` | ~60 | Client auth hook wrapping WorkOS useAuth |
| `frontend/hooks/use-queries.ts` | ~100 | TanStack Query hooks for all API data fetching |
| `frontend/hooks/use-audit-stream.ts` | ~70 | WebSocket hook for real-time audit/analysis updates |
| `frontend/lib/query-client.ts` | ~30 | TanStack QueryClient factory with defaults |
| `frontend/components/providers.tsx` | ~25 | Unified QueryClientProvider + AuthKitProvider wrapper |
| `frontend/lib/utils.ts` | ~30 | cn(), formatCredits(), formatCurrency(), formatDate() |
| `frontend/lib/logger.ts` | ~50 | Structured logger with context constants |
| `frontend/lib/supabase.ts` | ~~REMOVED~~ | Dead Supabase client — all data now exclusively through FastAPI |

### Route Map

| Route | Type | Auth | Description |
|-------|------|------|-------------|
| `/` | Static | No | Landing page: Hero + FeaturesGrid + AnalysisSelector + CTA |
| `/features` | Static | No | Marketing: 11 analysis types + 3 modes |
| `/pricing` | Static | No | Pricing tiers + credit packages + FAQ |
| `/login` | Route handler | No | WorkOS OAuth redirect |
| `/callback` | Route handler | No | WorkOS OAuth callback handler |
| `/auth/login` | Client page | No | Login UI with sign-in button |
| `/auth/logout` | Client page | Yes | Logout confirmation |
| `/dashboard` | Server page | Yes | Credit balance + recent audits (SSR) |
| `/audits` | Server page | Yes | Paginated audit list (status filter) |
| `/audit/[id]` | Client page | Yes | Audit results with WebSocket real-time updates |
| `/analyses` | Client page | Yes | Analysis list with status badges |
| `/analysis/[id]` | Client page | Yes | Analysis results with WebSocket real-time updates |
| `/credits` | Server page | Yes | Purchase credits (manual payment flow) |
| `/credits/history` | Client page | Yes | Transaction history |
| `/credits/requests` | Client page | Yes | Credit request list + proof upload |
| `/admin/credits` | Server page | Yes | Admin approve/reject credit requests |

### Auth Architecture

```
WorkOS AuthKit Flow:

/middleware.ts: authkitMiddleware()
  ├─ Public paths: /, /login, /signup, /api/auth/:path*, /features, /pricing
  └─ All others: require auth

Sign-in:
  /login → getSignInUrl() → WorkOS hosted auth page → OAuth (Google/GitHub)
  → /callback → handleAuth() → session cookie set

Sign-out:
  signOutAction() (server action) → clear WorkOS session → redirect /

Server Components:
  withAuth() → get access token → api.ts adds Bearer header

Client Components:
  useAuthUser() hook → getAccessToken() → api.ts receives token param
```

### Component Map

| Component | Path | Responsibility |
|-----------|------|----------------|
| `AnalysisSelector` | `components/analysis/` | 3-tab analysis launcher (Individual/Page/Site audit), URL discovery, cost estimation, execution |
| `AuditForm` | `components/audit/` | Simplified single-URL audit form with optimistic updates |
| `AuthButton` | `components/auth/` | Sign-in/sign-out button with user profile dropdown |
| `CreditBalance` | `components/credits/` | Real-time credit balance widget |
| `PurchaseCredits` | `components/credits/` | Credit calculator + manual payment flow |
| `Header` | `components/layout/` | Sticky header: logo, nav, credit balance, user menu |
| `HeroSection` | `components/marketing/` | Landing page hero |
| `FeaturesGrid` | `components/marketing/` | Feature cards grid |
| `CTASection` | `components/marketing/` | Call-to-action section |
| `SEOLogo` | `components/marketing/` | SEO Pro logo SVG |
| `Button` | `components/ui/` | shadcn button variant system |
| `Card` | `components/ui/` | Card with header/content/footer |
| `Dialog` | `components/ui/` | Modal dialog (Radix) |
| `Badge` | `components/ui/` | Status badge with variants |
| `Input` | `components/ui/` | Form input |
| `Progress` | `components/ui/` | Progress bar |
| `Tabs` | `components/ui/` | Tab interface (Radix) |
| `Select` | `components/ui/` | Dropdown select |
| `Toast` | `components/ui/` | Toast notifications |

### AnalysisSelector — Core Component (576 lines)

The most complex frontend component, handling all three analysis modes:

**Individual tab**: Pick from 12 analysis types, shows live cost estimate

**Page Audit tab**: Runs all 12 types on a single URL, shows 8 credit cost (33% bundle discount)

**Site Audit tab**:
1. URL input → `discoverSiteURLs()` → sitemap parsing
2. URL checklist with select/deselect all
3. Fallback to manual sitemap input
4. `estimateAnalysis()` → shows credit cost
5. `runAnalysis()` → redirects to `/analysis/[id]` or `/audit/[id]`

### State Management

State handled through:
- **Server state**: TanStack Query via `hooks/use-queries.ts` — declarative `useQuery`/`useMutation` hooks wrapping all `lib/api.ts` functions. Caching with stale times (30s for balance, 5s for audits). Mutations auto-invalidate related queries.
- **Client state**: `useState` for local/UI state (form inputs, dialog open/close, selection sets)
- **Auth state**: WorkOS `useAuth()` + `useAccessToken()` via `useAuthUser()` wrapper
- **Optimistic updates**: `useMutation` with `onMutate` for instant feedback
- **URL state**: `searchParams` for filters/pagination
- **Real-time updates**: WebSocket via `use-audit-stream.ts` — receives push events from Postgres LISTEN/NOTIFY, updates query cache via `queryClient.setQueryData()`. Eliminates all polling.

### Data Fetching Architecture

All data flows through `lib/api.ts` — a single unified API client used by both server and client components. Server components call API functions directly with `accessToken` from `withAuth()`. Client components use TanStack Query hooks from `hooks/use-queries.ts` which wrap the same API functions.

- **`lib/api.ts`** (universal): Takes optional `token` parameter. Used by both server components (directly) and client components (via TanStack Query hooks).
- ~~`lib/api-client.ts`~~ — **REMOVED (2026-05-23)**. Superseded by `lib/api.ts` which serves both server and client contexts.

### API Endpoints Consumed

The frontend calls these FastAPI endpoints:

| Endpoint | Used In |
|----------|---------|
| `GET /api/v1/credits/balance` | CreditBalance, Dashboard |
| `GET /api/v1/credits/history` | CreditsHistoryPage |
| `GET/POST /api/v1/credits/requests` | PurchaseCredits, CreditRequestsPage |
| `POST /api/v1/credits/requests/{id}/proof` | CreditRequestsPage |
| `POST /api/v1/audit/discover` | AnalysisSelector (site audit) |
| `POST /api/v1/audit/estimate` | AnalysisSelector, AuditForm |
| `POST /api/v1/audit/run` | AnalysisSelector |
| `GET /api/v1/audit/{id}` | AuditPage |
| `GET /api/v1/audit` | AuditsPage |
| `POST /api/v1/analyze/estimate` | AnalysisSelector |
| `POST /api/v1/analyze/{type}` | AnalysisSelector |
| `GET /api/v1/analyses` | AnalysesPage |
| `GET /api/v1/analyses/{id}` | AnalysisPage |
| `GET /api/v1/admin/credits/requests` | AdminCreditsPage |
| `POST /api/v1/admin/credits/requests/{id}/approve` | AdminCreditsPage |
| `POST /api/v1/admin/credits/requests/{id}/reject` | AdminCreditsPage |

### Tailwind / shadcn/ui Integration

- `components/ui/` follows shadcn/ui convention (Radix primitives + Tailwind styling)
- `class-variance-authority` for variant props
- `tailwind-merge` + `clsx` for `cn()` utility
- `lucide-react` for icons
- Dark mode not implemented (light-only theme)
