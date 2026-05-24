# 01 — System Architecture

> **Current-state review, not target architecture:** This file documents the system as it exists today and as it evolved during the prior review. The analysis/audit flow is being redesigned. Use [../ANALYSIS_FLOW_ARCHITECTURE.md](../ANALYSIS_FLOW_ARCHITECTURE.md) and [11-analysis-flow-current-and-target.md](./11-analysis-flow-current-and-target.md) as the source of truth for the intended quote/job/result architecture.

## High-Level Architecture

SEO Pro uses a **microservices-inspired architecture** deployed on Google Cloud Platform with two primary user interfaces (SaaS web app and CLI skill).

### Deployment Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                        USERS                                      │
│  ┌─────────────────┐              ┌───────────────────────────┐  │
│  │  Browser         │              │  Claude Code CLI           │  │
│  │  (SaaS Platform) │              │  (Skill Mode)              │  │
│  └───────┬─────────┘              └───────────┬───────────────┘  │
└──────────┼────────────────────────────────────┼──────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────┐           ┌──────────────────────────────┐
│  Vercel (Frontend)   │           │  Local Filesystem             │
│  Next.js 15 SSR      │           │  skills/, agents/, scripts/  │
└──────────┬───────────┘           └──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                          │
│                                                                   │
│  ┌─────────────────────┐     ┌──────────────────────────────┐   │
│  │  Cloud Run: Gateway  │────▶│  Cloud Tasks: seo-audit-queue │   │
│  │  (FastAPI, 512Mi)    │     │  (Task queue for async jobs)  │   │
│  └──────────┬──────────┘     └──────────────┬───────────────┘   │
│             │                               │                     │
│             ▼                               ▼                     │
│  ┌─────────────────────┐     ┌──────────────────────────────┐   │
│  │  Supabase            │     │  Cloud Run: SDK Worker        │   │
│  │  (Managed PostgreSQL)│     │  (Claude Agent SDK, 4Gi)      │   │
│  └─────────────────────┘     └──────────────┬───────────────┘   │
│                                              │                    │
│                                              ▼                    │
│                                    ┌──────────────────────────┐  │
│                                    │  Claude Agent SDK Runtime  │  │
│                                    │  Skills + Agents + Scripts │  │
│                                    │  + Playwright MCP          │  │
│                                    └──────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Secret Manager                                           │   │
│  │  SUPABASE_SECRET_KEY, WORKOS_CLIENT_ID, SENDGRID_API_KEY   │   │
│  │  ANTHROPIC_AUTH_TOKEN (Z.AI API)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  WorkOS (External SaaS)                                    │   │
│  │  OAuth SSO: Google, GitHub — JWT issuance + verification   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Service Boundaries

| Service | Technology | Hosting | Port | Resources |
|---------|------------|---------|------|-----------|
| **Frontend** | Next.js 15 | Vercel | 443 | Serverless |
| **Gateway** | FastAPI | Cloud Run | 8080 | 512Mi, 1 CPU, 0-100 instances |
| **SDK Worker** | FastAPI + Claude SDK | Cloud Run | 8080 | 4Gi, 2 CPU, 0-10 instances |
| **Database** | PostgreSQL 17 | Supabase (managed) | 5432 | Managed |
| **Task Queue** | Cloud Tasks | GCP | — | Managed |

### Data Flow — Full Site Audit (Current Legacy Flow)

This is the current site-audit flow. It is not the target architecture for all analysis modes. The intended direction is one durable quote/request lifecycle, one async paid-job lifecycle, and one `/analysis/{analysis_id}` result route for individual, page, and site analysis.

```
1. User submits URL on Frontend
   → POST /api/v1/audit/discover (or /analyze/page)

2. Gateway (FastAPI):
   a. Verify JWT (WorkOS) → get user ID
   b. Validate URL (SSRF check)
   c. SiteScanner discovers URLs (sitemap + crawl)
   d. Calculate credits (7 × page count)
   e. Create pending_audits quote (30min TTL)

3. User confirms and pays:
   a. Deduct credits atomically (PostgreSQL FOR UPDATE)
   b. Create audits record
   c. Submit to Cloud Tasks queue

4. Cloud Tasks delivers to SDK Worker:
   POST /analyze with {url, analysis_type, page_urls}

5. SDK Worker:
   a. Validates URL
   b. Invokes Claude Agent SDK with prompt
   c. Agent SDK loads skills/ + agents/ from filesystem
   d. seo-audit skill delegates to 6 parallel subagents
   e. Results returned to worker

6. Worker writes results to Supabase:
   a. Current site-audit path updates audits when audit_id is present
   b. audit_tasks is only updated when a task_id is provided
   c. No orchestrator callback path remains

7. Frontend observes status:
   GET /api/v1/audit/{id} and audit-centered WebSocket events are used for site audits
   → Target state moves all paid jobs to /analysis/{analysis_id}
```

### Request Authentication Flow

```
Browser → Next.js → WorkOS AuthKit (SSO)
  │
  │  OAuth callback → WorkOS session cookie
  │
  ▼
Frontend pages:
  - Server Components: withAuth() → get access token → Bearer to Gateway
  - Client Components: useAuthUser() → getAccessToken() → Bearer to Gateway

Gateway:
  - Extract Bearer token from Authorization header
  - Verify JWT with WorkOS public keys (JWKS, cached 15 min)
  - Sync/upsert user in Supabase
  - Inject user into route handler via Depends(get_current_user)
```

### Pricing/Credit Model

| Analysis Mode | Credits | $ Equivalent | Notes |
|---------------|---------|-------------|-------|
| Individual (1 type) | 1 | ~$0.12 | Per analysis type |
| Full Page Audit | 8 | ~$1.00 | All 12 types bundled (33% off) |
| Full Site Audit | 7/page | ~$0.88/page | All 12 types × page count |
| **Exchange Rate** | **$1 = 8 credits** | Never expire | Minimum top-up: $8 (64 credits) |

### Two Operating Modes

**SaaS Platform** — Full web application:
- WorkOS AuthKit SSO
- Credit-based purchasing
- Dashboard with history
- Admin panel for credit approvals
- Deployed on Vercel + Cloud Run

**Claude Code Skill** — CLI tool:
- Installed via `curl | bash` (install.sh) or `irm | iex` (install.ps1)
- 10 slash commands: `/seo audit`, `/seo page`, `/seo schema`, etc.
- Uses same skills/ and agents/ as cloud deployment
- Runs Claude Agent SDK locally
- MCP integration for Playwright, Ahrefs, Semrush

### Key Architectural Decisions

1. **Filesystem-based skills/agents**: Same `.md` files used by both CLI and cloud, no duplication
2. **Unified SDK worker**: Replaced separate HTTP + Browser workers, all analysis through Claude Agent SDK
3. **Credit atomicity**: PostgreSQL `FOR UPDATE` row locks prevent race conditions on credit deductions
4. **JWKS caching**: Thread-safe, 15-min TTL, async lock with double-check pattern
5. **SSRF protection**: Multi-layer validation before any outbound HTTP request
6. **DEV_MODE flag**: Unlimited credits for development, blocked from production by config validator
7. **Manual payment flow**: No IPG integration — users request credits, upload proof, admins approve
8. **Real-time updates**: WebSocket + Postgres LISTEN/NOTIFY exists for audit status. The analysis-flow tracker documents the remaining route/event-model gaps and the target analysis-centered realtime contract.
