# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-05-23

### Removed - Legacy Orchestrator (Cleanup)

The legacy orchestrator service has been fully removed. It had been bypassed by the API Gateway directly dispatching to the unified SDK Worker via Cloud Tasks, creating confusion about which code path was correct. The orchestrator also used in-memory state (`_audit_state = {}`) that would be lost on Cloud Run restart or scale events.

- **Removed**: `orchestrator/scheduler.py` — legacy audit orchestration with in-memory state tracking
- **Removed**: `deploy/Dockerfile.orchestrator` — no longer built or deployed
- **Removed**: `frontend/lib/api-client.ts` — unused API client superseded by `lib/api.ts`
- **Cleaned**: `docker-compose.yml` — removed orchestrator service definition
- **Cleaned**: `api/config.py` — removed orchestration-specific settings and env vars
- **Cleaned**: `api/services/` — removed orchestrator proxy code in `audits.py` and `cloud_tasks.py`
- **Cleaned**: `.github/workflows/ci.yml` — removed `ruff check orchestrator/` and Dockerfile.orchestrator build step
- **Cleaned**: `deploy/Dockerfile.gateway` — removed orchestrator copy step

*User perspective*: No impact — the orchestrator was already bypassed. The single audit path (API Gateway → Cloud Tasks → SDK Worker → Supabase) remains unchanged.

### Added - Code Review Documentation

Comprehensive architectural review covering all system components.

- **Added**: `docs/review/` — 10 review documents plus index (01-system-architecture through 10-findings)
- **Added**: `docs/review/README.md` — review index and navigation

### Added - Frontend State Management (TanStack Query)

Replaced manual `useState` + `useEffect` + `useRef` patterns with declarative TanStack Query hooks. This eliminates duplicate requests (e.g., `CreditBalance` and `CreditsHistoryPage` both independently fetching `/credits/balance`), provides built-in caching, and standardizes loading/error handling across all data-fetching components.

- **Added**: `@tanstack/react-query` dependency
- **Added**: `frontend/lib/query-client.ts` — QueryClient factory with sensible `staleTime`/`retry` defaults
- **Added**: `frontend/components/providers.tsx` — unified `QueryClientProvider` + `AuthKitProvider` wrapper
- **Added**: `frontend/hooks/use-queries.ts` — custom hooks replacing all manual data fetching:
  - `useCreditBalance()` with 30s stale time (avoids refetch on every mount)
  - `useCreditHistory()`, `useCreditRequests()` for credit pages
  - `useAuditsList()`, `useAnalysesList()` for list pages with filtering
  - `useAuditStatus()`, `useAnalysisStatus()` with conditional `refetchInterval` (stops on completion)
  - `useCreateCreditRequest()`, `useSubmitPaymentProof()` mutations with automatic cache invalidation

- **Updated**: `CreditBalance` — uses `useCreditBalance()` instead of manual `useState` + `useEffect`
- **Updated**: `PurchaseCredits` — uses `useCreateCreditRequest()` mutation
- **Updated**: `CreditsHistoryPage` — uses `useCreditHistory()` + `useCreditBalance()`, automatic cache sharing with header component
- **Updated**: `CreditRequestsPage` — uses `useCreditRequests()` + `useSubmitPaymentProof()` mutation
- **Updated**: `AnalysesListPage` — uses `useAnalysesList()` instead of manual `useState` + `useEffect`
- **Updated**: `frontend/app/layout.tsx` — uses new `Providers` component wrapping both auth and query providers

*User perspective*: Smoother UI — credit balance in the header and credit history page share the same cached data, no flickering duplicate loads. Operation loading states are consistent across all pages.

*Dev perspective*: Standardized data fetching pattern. Adding a new API-backed component is now `useQuery({ queryKey: [...], queryFn: apiFunc })` instead of manual state management. Mutations automatically invalidate related queries.

### Added - Real-Time Audit Status via WebSocket + Postgres LISTEN/NOTIFY

Replaced HTTP polling (2-second intervals for audits, 5-second for analyses) with push-based real-time updates. The entire stack is event-driven — zero polling anywhere.

- **Added**: `supabase/migrations/002_audit_change_trigger.sql` — DB trigger that fires `pg_notify('audit_changes', payload)` on every audit table update
- **Added**: `api/routes/ws.py` — WebSocket endpoint `wss://gateway/api/v1/audit/{id}/stream` with asyncpg LISTEN subscription
- **Added**: `api/core/ws_auth.py` — WorkOS JWT validation extracted from WebSocket query parameters
- **Added**: `frontend/hooks/use-audit-stream.ts` — WebSocket client hook that updates TanStack Query cache via `queryClient.setQueryData()`
- **Added**: `asyncpg>=0.30.0` dependency for direct Postgres connection pool
- **Added**: `api/config.py` — new `SUPABASE_DATABASE_URL` setting for direct Postgres connections
- **Updated**: `api/main.py` — startup/shutdown hooks for asyncpg pool lifecycle, registers WebSocket router
- **Updated**: `AuditPage` (`frontend/app/audit/[id]/page.tsx`) — uses `useAuditStatus()` + `useAuditStream()` instead of manual `useEffect` polling
- **Updated**: `AnalysisResultsPage` (`frontend/app/analysis/[id]/page.tsx`) — uses `useAnalysisStatus()` + `useAnalysisStream()` instead of manual `useEffect` polling

**Architecture:**
```
Worker writes to Supabase
  → DB trigger: pg_notify('audit_changes', payload)
    → FastAPI Gateway: asyncpg LISTEN on WebSocket connect
      → wss:// gateway sends events to frontend
        → queryClient.setQueryData(['audit', id], payload)
```

*User perspective*: Instant status transitions — the spinner switches from "queued" to "processing" to "completed" without the 2-second polling delay. No more flickering refresh cycles.

*Dev perspective*: No polling anywhere in the stack. LISTEN/NOTIFY is event-driven (Postgres pushes when data changes, not on a timer). WebSocket reconnects automatically with 2-second backoff if the connection drops (e.g., Cloud Run 300s timeout). WorkOS remains the only auth system — token is passed as a WebSocket query parameter and validated by the Gateway before subscribing.

### Removed - Dead Supabase Frontend Client

The Supabase JS client in the frontend (`lib/supabase.ts`) was set up but never used — all data access flows through the FastAPI Gateway. This created confusion for new developers and added dead weight to the bundle.

- **Removed**: `frontend/lib/supabase.ts` — unused Supabase client with TypeScript interfaces
- **Removed**: `@supabase/supabase-js` from frontend dependencies
- **Removed**: `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from `docker-compose.yml` frontend service
- **Removed**: `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` from `docs/DEPLOYMENT.md` frontend section

*User perspective*: No impact — the client was never functional (env var name mismatch between `ANON_KEY` in docker-compose and `PUBLISHABLE_KEY` in the client).

*Dev perspective*: Clear separation — all data flows through FastAPI. No ambiguity about whether to use the Supabase client or the API client.

### Changed - WorkOS AuthKit Configuration & JWT Validation

Overhauled the WorkOS authentication configuration to match AuthKit's actual token structure. AuthKit session tokens do not include an `aud` claim by default, and the issuer is namespaced per client — the previous config was using generic WorkOS API credentials rather than AuthKit-specific endpoints.

**Root cause:** The `env_prefix` in pydantic-settings was silently ignoring all unprefixed `.env` variables, causing the app to always use defaults (like `WORKOS_AUDIENCE=api.workos.com` and `WORKOS_ISSUER=api.workos.com`) regardless of what was actually set in the `.env` file.

- **Fixed**: `api/config.py` — removed `env_prefix: "SEO_PRO_"` from `SettingsConfigDict` (was silently dropping all unprefixed env vars)
- **Changed**: `WORKOS_AUDIENCE` from required `str` to `Optional[str]` defaulting to `None` (AuthKit tokens don't include `aud` by default)
- **Removed**: `WORKOS_ISSUER` field entirely — AuthKit tokens use a client-specific issuer, not the generic WorkOS API issuer
- **Fixed**: `WORKOS_JWKS_URL` from `https://api.workos.com/v1/jwks` to `https://api.workos.com/sso/jwks/{client_id}` — the correct AuthKit JWKS endpoint
- **Added**: `WORKOS_API_KEY` setting — enables server-side WorkOS API calls for user profile lookup
- **Changed**: `workos_audience` property — returns `None` for default values, disabling audience verification when not configured
- **Removed**: `workos_issuer` computed property — no longer needed
- **Updated**: `api/services/auth.py` — formats JWKS URL with `client_id`, skips `aud`/`iss` verification when not configured
- **Added**: JWKS cache invalidation on key rotation — if the cached JWKS doesn't contain the token's `kid`, the cache is flushed and re-fetched before failing
- **Updated**: `api/conftest.py` — simplified test env setup, removed `WORKOS_ISSUER`
- **Updated**: `.env.example` — updated WorkOS config docs with correct AuthKit values
- **Updated**: `docs/DEPLOYMENT.md`, `docs/LOCAL_DEVELOPMENT.md` — deployment and dev docs reflect new config
- **Removed**: `WORKOS_AUDIENCE` and `WORKOS_ISSUER` from `validate_required_settings()` — no longer required

*User perspective*: No visible change — authentication continues to work. Previously, if the `.env` had correct values they were being silently ignored; now env vars are properly read.

*Dev perspective*: AuthKit workflow now matches WorkOS documentation. The JWK URL is correct per AuthKit spec (`/sso/jwks/{client_id}` not `/v1/jwks`). Audience/issuer verification is opt-in rather than incorrectly asserted. The `env_prefix` bug is fixed — all `.env` variables are now read regardless of naming convention.

### Changed - Real User Profile Sync from WorkOS

`sync_user_to_supabase()` now fetches the full user profile from the WorkOS API instead of relying on AuthKit JWT claims. AuthKit JWTs only carry `sub`/`sid`/`org_id`/`role` — email and name come from the identity provider (Google, GitHub, etc.) and require a server-side API call.

- **Added**: `_fetch_workos_user()` in `api/services/auth.py` — fetches real `email`, `first_name`, `last_name` from WorkOS `user_management.get_user()` API
- **Changed**: `sync_user_to_supabase()` — fetches WorkOS profile on every login (new and existing users)
- **Changed**: Existing users now get profile data refreshed (email, first_name, last_name) on each login instead of just `last_sync`
- **Changed**: New users are created with real IdP profile data instead of `@placeholder.local` fallback emails
- **Added**: Graceful degradation — if WorkOS API key is not configured, falls back to JWT claims (logged as warning)

*User perspective*: Users will see their real name and email (from Google/GitHub SSO) in the app immediately instead of placeholder values.

*Dev perspective*: Requires `WORKOS_API_KEY` env var for the profile fetch to work. Without it, the system logs a warning and falls back to JWT claims. Follows taste.md guidance: "When using WorkOS AuthKit with social providers, sync real user profile data from the identity provider to Supabase, not placeholder values."

### Added - Auth & Schema Regression Tests

- **Added**: `api/tests/test_auth.py` — 3 JWT verification tests:
  - Verifies AuthKit session tokens are accepted with legacy `aud`/`iss` env defaults
  - Verifies AuthKit tokens signed with the correct WorkOS issuer pass validation
  - Verifies JWKS cache invalidation on key rotation (refetches and retries before rejecting)
- **Added**: `api/tests/test_workos_schema.py` — 3 database schema regression tests:
  - Verifies WorkOS IDs (`user_xxx`, `org_xxx`) are stored as `TEXT`, not `UUID`
  - Verifies all foreign keys and function parameters accept `TEXT` user IDs
  - Verifies RLS policies use `auth.jwt() ->> 'sub'` (text) not `auth.uid()` (UUID)

### Changed - Frontend Auth & Data Fetching Fixes

Fixed a race condition where TanStack Query hooks would fire before the access token was fully loaded, causing 401 errors on initial page load. Also fixed the middleware to allow AuthKit callback URLs.

- **Fixed**: `frontend/hooks/use-queries.ts` — changed `enabled` from `isAuthenticated` to `canFetch` (checks both `isAuthenticated` and `!accessTokenLoading`)
- **Fixed**: `useAuditStatus` and `useAnalysisStatus` — added missing `canFetch` check to their `enabled` conditions
- **Added**: `frontend/hooks/use-auth.ts` — exports new `accessTokenLoading` state
- **Fixed**: `frontend/hooks/use-queries.ts` — all query hooks now use `canFetch` instead of just `isAuthenticated`
- **Fixed**: `frontend/middleware.ts` — added `/callback` to public paths (AuthKit callback route was being blocked)
- **Changed**: `frontend/app/dashboard/page.tsx` — credit balance is now fetched client-side via `useCreditBalance()` hook instead of server-side `getCreditBalance()`, eliminating a redundant server fetch and allowing the dashboard to show a loading state
- **Changed**: `frontend/app/dashboard/dashboard-content.tsx` — uses `useCreditBalance()` hook internally; shows "..." while loading credits

*User perspective*: No more spurious 401 errors on initial page load. Credit balance on the dashboard shows a loading state while fetching. AuthKit callback flow works correctly.

*Dev perspective*: All data-fetching hooks now properly wait for the access token to be ready before firing. This was a subtle race — `isAuthenticated` was `true` before `getAccessToken()` returned a resolved token.

### Changed - Database Migration Consolidation

Following the taste.md guidance to consolidate DB changes into the initial migration during pre-production, the audit change trigger has been moved from its own migration file into `001_initial_schema.sql`.

- **Moved**: `notify_audit_change()` function and `audit_changed` trigger from `002_audit_change_trigger.sql` into `001_initial_schema.sql`
- **Deleted**: `supabase/migrations/002_audit_change_trigger.sql` — no longer a separate migration

*Dev perspective*: Single migration file reduces complexity for `supabase db push`. The consolidated schema is cleaner and easier to review.

### Added - Skills Infrastructure & PayPal Sandbox Plan

- **Added**: `.agents/skills/supabase/` — Supabase skills (SKILL.md, references) from the public `supabase/agent-skills` GitHub repository
- **Added**: `skills-lock.json` — locks supabase and supabase-postgres-best-practices skills to specific hashes
- **Added**: `.mcp.json` — PayPal MCP server configuration for sandbox testing
- **Added**: `docs/plans/2026-05-23-paypal-payment-links-sandbox.md` — detailed sandbox experiment plan for PayPal Payment Links reconciliation

### Changed - Taste System Architecture Guidance

Extended `.commandcode/taste/taste.md` with learned preferences:
- Route all frontend data access through the FastAPI backend, not directly to Supabase
- For real-time status updates, use Postgres LISTEN/NOTIFY + FastAPI WebSocket rather than Supabase Realtime
- Sync real user profile data from WorkOS IdP to Supabase (not placeholder values)
- Avoid `env_prefix` in pydantic-settings (silently ignores unprefixed env vars)
- Consolidate DB changes into initial migration during pre-production
- Store plan files in project-local `.commandcode/plan/` directory
- Debug by tracing existing code-level relationships (follow the breadcrumb trail)
- After fixing one issue, continue investigating for other overlooked issues
- When identifying code duplication, consolidate to the correct pattern first
- Kill servers after making changes (user manages their own server processes)



## [2.1.0] - 2026-02-28

### Added - Manual Payment Flow

This release replaces the PayHere payment gateway (Sri Lanka-only) with a manual payment flow supporting international payments via Wise/Bank transfer.

#### Credit Request System
- **Manual Payment Flow**: Users request credits, receive invoice, upload payment proof
- **Invoice Generation**: Automatic unique invoice numbers (format: `INV-YYYYMMDD-XXXXXX`)
- **Payment Proof Upload**: Users upload payment confirmations for admin review
- **Status Tracking**: `pending` → `proof_uploaded` → `approved`/`rejected`
- **Credit Request History**: View all past requests at `/credits/requests`

#### Admin Dashboard
- **Admin Credit Management**: New `/admin/credits` page for managing requests
- **Status Filtering**: Filter by pending, proof_uploaded, approved, rejected
- **One-Click Approval**: Add credits to user balance with confirmation
- **Rejection with Reason**: Required reason field for transparency
- **Admin Access Control**: Email-based admin verification via `ADMIN_EMAILS` env var

#### Email Notifications (SendGrid)
- **Credit Request Confirmation**: Sent to user when request is created
- **Payment Proof Notification**: Sent to admins when proof is uploaded
- **Credit Approval Notification**: Sent to user when credits are added
- **Credit Rejection Notification**: Sent to user with rejection reason
- **HTML Email Templates**: Professional branded email templates

### Added - Analysis Tracking

- **Analysis Records**: Individual analyses now tracked in `analyses` table
- **Status Tracking**: `pending` → `processing` → `completed`/`failed`
- **Credits Used**: Records credits consumed per analysis
- **Error Tracking**: Failed analyses record error messages

### Added - API Endpoints

#### Credit Requests
- `POST /api/v1/credits/requests` - Create credit request
- `GET /api/v1/credits/requests` - List user's requests
- `GET /api/v1/credits/requests/{id}` - Get specific request
- `POST /api/v1/credits/requests/{id}/proof` - Upload payment proof

#### Admin
- `GET /api/v1/admin/credits/requests` - List all credit requests
- `GET /api/v1/admin/credits/requests/{id}` - Get specific request
- `POST /api/v1/admin/credits/requests/{id}/approve` - Approve request
- `POST /api/v1/admin/credits/requests/{id}/reject` - Reject request
- `POST /api/v1/admin/credits/cleanup/expired-quotes` - Clean expired quotes

#### Internal
- `POST /api/v1/internal/cleanup/expired-quotes` - Scheduled cleanup endpoint

### Changed - Infrastructure

#### Environment Variables (Renamed)
- `SUPABASE_SERVICE_KEY` → `SUPABASE_SECRET_KEY` (clearer naming)
- `SUPABASE_ANON_KEY` → `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (clearer naming)

#### Structured Logging
- Replaced all `print()` statements with Python `logging` module
- Structured log format with `extra` fields for context
- Better observability in Cloud Run logs

#### Worker Reliability
- Added retry logic with exponential backoff for worker calls
- Uses `tenacity` library for connection failure retries
- Max 3 attempts with 1-10 second backoff

#### CORS Security
- Restricted from `allow_methods=["*"]` to explicit method list
- Restricted from `allow_headers=["*"]` to explicit header list

#### Frontend
- Added automatic token refresh every minute in `useAuth` hook
- Updated purchase credits component for manual payment flow
- Added credit requests page with status tracking

### Changed - Database Schema

#### New Tables
- `credit_requests` - Manual payment flow tracking
- `analyses` - Individual analysis tracking with status

#### Removed Tables/Columns
- `plan_tier` column from `users` (simplified pricing)
- `payment_id` column from `credit_transactions` (PayHere-specific)
- `credits` table (redundant with credit_transactions)
- `pending_orders` table (PayHere-specific)
- `audit_pages` table (not used)
- `cached_pages` table (not used)

#### New Functions
- `cleanup_expired_quotes()` - Delete expired pending audits
- `cleanup_expired_quotes_with_stats()` - Returns deletion stats
- `create_analysis_record()` - Create analysis with status
- `update_analysis_record()` - Update analysis status/results
- `refund_credits()` - Dedicated refund function

### Added - Configuration

| Setting | Description |
|---------|-------------|
| `ADMIN_EMAILS` | Comma-separated admin email addresses |
| `SENDGRID_API_KEY` | SendGrid API key for email delivery |
| `SENDGRID_FROM_EMAIL` | Verified sender email address |
| `SENDGRID_FROM_NAME` | Display name for sent emails |

### Added - Dependencies

- `sendgrid>=6.9.0` - Email delivery
- `tenacity>=8.2.0` - Retry logic

### Added - Documentation

- Updated `docs/DEPLOYMENT.md` with SendGrid setup and manual payment flow
- Updated `docs/TODO.md` with infrastructure improvements

### Removed

- `api/routes/audit.py` - Empty placeholder file
- `supabase/migrations/002_analysis_tracking.sql` - Merged into 001
- `supabase/migrations/003_refund_credits_function.sql` - Merged into 001

---

## [2.0.0] - 2026-02-26

### Added - SaaS Platform (MAJOR)

This release transforms SEO Pro from a CLI-only tool into a full SaaS platform while maintaining 100% backward compatibility with the Claude Code Skill mode.

#### Web Application
- **Next.js Frontend**: TypeScript + Tailwind CSS + shadcn/ui components
- **FastAPI Gateway**: RESTful API with authentication, credits, and orchestration
- **WorkOS AuthKit**: Enterprise-grade authentication with SSO support (Google, GitHub, etc.)
- **Supabase PostgreSQL**: Multi-tenant database with Row-Level Security (RLS)
- **Docker Compose**: One-command local development environment

#### Credit System
- **Credit-Based Pricing**: $1 = 8 credits with tiered analysis costs
- **Real-Time Balance Tracking**: Live credit balance updates
- **Atomic Operations**: Race-condition-safe credit deduction with PostgreSQL transactions
- **Transaction History**: Complete audit trail of all credit activity
- **Never-Expiring Credits**: Purchase once, use anytime
- **Dev Mode**: Unlimited access for development/testing

#### Analysis Pricing
| Mode | Credits | Description |
|------|---------|-------------|
| Quick Analysis | 1 per report | Individual analysis types |
| Full Page Audit | 8 per page | All 12 types on one page (33% discount) |
| Full Site Audit | 7 per page | All 12 types across entire site |

#### Cloud Deployment
- **Google Cloud Run**: Scale-to-zero serverless deployment
- **Cloud Tasks**: Async job processing with `sdk-worker-queue`
- **Secret Manager**: Secure API key storage
- **CI/CD Pipeline**: GitHub Actions workflow for automated deployments

### Changed - Worker Architecture (BREAKING)

#### Unified SDK Worker
- **Migration**: Replaced `browser_worker` and `http_worker` with unified `sdk_worker`
- **Claude Agent SDK**: Filesystem-based Skills and Agents for multi-agent orchestration
- **GLM-4.7 Integration**: Z.AI API for cost-effective AI analysis via Anthropic-compatible endpoint
- **Playwright CLI**: Browser automation via concise Bash commands (vs MCP tool schemas)

#### API Restructure
- **Modular Architecture**: `api/core/`, `api/models/`, `api/services/`, `api/routes/`
- **Dedicated Route Modules**: `analyses.py`, `audits.py`, `credits.py`, `health.py`
- **Centralized Dependencies**: `api/core/dependencies.py` for shared services
- **Comprehensive Models**: Pydantic models for all request/response types

### Added - Frontend Components

#### Pages
- `/analyses` - Analysis history with filtering by type/status
- `/analysis/[id]` - Detailed analysis results with scores and recommendations
- `/audits` - Full site audit management
- `/audit/[id]` - Audit progress and results
- `/credits` - Credit balance and purchase flow
- `/credits/history` - Transaction history
- `/pricing` - Pricing tiers and feature comparison
- `/features` - Feature showcase with 12 analysis types

#### Components
- **Analysis Selector**: Interactive tool to choose analysis types with live cost preview
- **Audit Form**: URL input with site discovery and cost estimation
- **Auth Button**: WorkOS login/logout with user profile display
- **Credit Balance**: Real-time balance widget
- **Error Boundary**: Graceful error handling with retry

### Added - Security Features

- **SSRF Prevention**: URL validation with private IP blocking
- **Row-Level Security**: Data isolation per user/organization in Supabase
- **JWT Authentication**: WorkOS token validation with audience verification
- **CORS Configuration**: Origin whitelisting for API access
- **Input Sanitization**: Injection prevention across all endpoints

### Added - API Endpoints

#### System
- `GET /api/v1/health` - Service health check
- `GET /api/v1/health/ready` - Dependency readiness check

#### Credits
- `GET /api/v1/credits/balance` - Current credit balance
- `GET /api/v1/credits/history` - Transaction history with pagination

#### Audits
- `POST /api/v1/audit/discover` - Discover site URLs from sitemap/crawling
- `POST /api/v1/audit/estimate` - Get cost estimate before running
- `POST /api/v1/audit/run` - Execute full site audit
- `GET /api/v1/audit/{id}` - Audit status and results
- `GET /api/v1/audit` - List user's audits with filtering

#### Analysis
- `POST /api/v1/analyze/estimate` - Estimate credits for any analysis
- `GET /api/v1/analyses` - List analyses with filtering
- `GET /api/v1/analyses/{id}` - Single analysis details
- `POST /api/v1/analyze/{type}` - Run individual analysis (12 types)
- `POST /api/v1/analyze/page` - Full page audit (all 12 types)

### Added - Database Schema

- `users` - User profiles and credit balances
- `organizations` - Multi-tenant structure
- `credit_transactions` - Complete audit trail
- `analyses` - Individual analysis tracking with status
- `audits` - Full site audit management
- `audit_tasks` - Subagent progress tracking
- `pending_audits` - Quote management for large audits
- `cached_pages` - 24-hour TTL cache for performance

### Added - Infrastructure

- **Dockerfiles**: `Dockerfile.gateway`, `Dockerfile.sdk-worker`
- **Docker Compose**: Full stack orchestration for local development
- **Cloud Build**: `cloudbuild.yaml` for automated deployments
- **Environment Config**: Centralized `config.py` with validation
- **Rate Limiting Documentation**: `docs/RATE-LIMITING.md`

### Added - Developer Experience

- **Local Development Guide**: `docs/LOCAL_DEVELOPMENT.md`
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Architecture Documentation**: Updated `docs/ARCHITECTURE.md`
- **Features Overview**: `docs/FEATURES.md` with pricing and capabilities
- **.env.example**: Template for all required environment variables

### Changed

- **Frontend Auth**: Migrated from `route.tsx` to `page.tsx` callback pattern
- **Auth Module**: Converted `lib/auth.ts` to `lib/auth.tsx` for React components
- **Documentation**: Reorganized docs into `docs/` folder
- **Rate Limiting**: Enhanced with configurable tiers and per-endpoint limits

### Removed

- `browser_worker.py` - Replaced by unified SDK worker
- `http_worker.py` - Replaced by unified SDK worker
- Legacy worker-specific Dockerfiles

---

## [1.1.0] - 2026-02-07

### Security (CRITICAL)
- **urllib3 ≥2.6.3**: Fixes CVE-2026-21441 (CVSS 8.9) - decompression bypass vulnerability
- **lxml ≥6.0.2**: Updated from 5.3.2 for additional libxml2 security patches
- **Pillow ≥12.1.0**: Fixes CVE-2025-48379
- **playwright ≥1.55.1**: Fixes CVE-2025-59288 (macOS)
- **requests ≥2.32.4**: Fixes CVE-2024-47081, CVE-2024-35195

### Added
- **GEO (Generative Engine Optimization) major enhancement**:
  - Brand mention analysis (3× more important than backlinks for AI visibility)
  - AI crawler detection (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, etc.)
  - llms.txt standard detection and recommendations
  - RSL 1.0 (Really Simple Licensing) detection
  - Passage-level citability scoring (optimal 134-167 words)
  - Platform-specific optimization (Google AI Overviews vs ChatGPT vs Perplexity)
  - Server-side rendering checks for AI crawler accessibility
- **LCP Subparts analysis**: TTFB, resource load delay, resource load time, render delay
- **Soft Navigations API detection** for SPA CWV measurement limitations
- **Schema.org v29.4 additions**: ConferenceEvent, PerformingArtsEvent, LoyaltyProgram
- **E-commerce schema updates**: returnPolicyCountry now required, organization-level policies

### Changed
- **E-E-A-T framework**: Updated for December 2025 core update - now applies to ALL competitive queries, not just YMYL
- **SKILL.md description**: Expanded to leverage new 1024-character limit
- **Schema deprecations expanded**: Added ClaimReview, VehicleListing (June 2025)
- **WebApplication schema**: Added as correct type for browser-based SaaS (vs SoftwareApplication)

### Fixed
- Schema-types.md now correctly distinguishes SoftwareApplication (apps) vs WebApplication (SaaS)

---

## [1.0.0] - 2026-02-07

### Added
- Initial release of SEO Pro
- 9 specialized skills: audit, page, sitemap, schema, images, technical, content, geo, plan
- 6 subagents for parallel analysis: seo-technical, seo-content, seo-schema, seo-sitemap, seo-performance, seo-visual
- Industry templates: SaaS, local service, e-commerce, publisher, agency, generic
- Schema library with deprecation tracking:
  - HowTo schema marked deprecated (September 2023)
  - FAQ schema restricted to government/healthcare sites only (August 2023)
  - SpecialAnnouncement schema marked deprecated (July 31, 2025)
- AI Overviews / GEO optimization skill (seo-geo) - new for 2026
- Core Web Vitals analysis using current metrics:
  - LCP (Largest Contentful Paint): <2.5s
  - INP (Interaction to Next Paint): <200ms - replaced FID on March 12, 2024
  - CLS (Cumulative Layout Shift): <0.1
- E-E-A-T framework updated to September 2025 Quality Rater Guidelines
- Quality gates for thin content and doorway page prevention:
  - Warning at 30+ location pages
  - Hard stop at 50+ location pages
- Pre-commit and post-edit automation hooks
- One-command install and uninstall scripts (Unix and Windows)
- Bounded Python dependency pinning with CVE-aware minimums (lxml >= 5.3.2)

### Architecture
- Follows Anthropic's official Claude Code skill specification (February 2026)
- Standard directory layout: `scripts/`, `references/`, `assets/`
- Valid hook matchers (tool name only, no argument patterns)
- Correct subagent frontmatter fields (name, description, tools)
- CLI command is `claude` (not `claude-code`)
