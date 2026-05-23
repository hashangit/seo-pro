# 02 — API Gateway

## Overview

The API gateway is a **FastAPI** application deployed on **Google Cloud Run** (512Mi, 1 CPU, 0–100 instances, 300s timeout). It serves as the central backend for the SaaS platform, handling authentication, credits, audit orchestration, and proxying analysis requests to the SDK Worker.

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `api/main.py` | ~70 | Entry point, router registration, startup/shutdown |
| `api/config.py` | ~100 | Centralized settings via pydantic-settings |
| `api/core/app.py` | ~40 | `create_app()` factory: FastAPI + CORS + middleware |
| `api/core/dependencies.py` | ~80 | `get_current_user()`, `get_internal_secret()` |
| `api/core/middleware.py` | ~40 | Security headers HTTP middleware |
| `api/rate_limiter.py` | ~120 | Per-endpoint rate limiting (Redis/memory) |

### Router Map

| Router | File | Prefix | Key Endpoints |
|--------|------|--------|---------------|
| `health` | `api/routes/health.py` | `/api/v1` | `GET /health`, `GET /health/ready`, `POST /internal/invalidate-jwks`, `POST /internal/cleanup/expired-quotes` |
| `credits` | `api/routes/credits.py` | `/api/v1/credits` | `GET /balance`, `GET /history`, `GET /purchase` |
| `credit_requests` | `api/routes/credit_requests.py` | `/api/v1/credits/requests` | `POST /`, `GET /`, `POST /{id}/proof`, `GET /{id}` |
| `admin_credits` | `api/routes/admin/credits.py` | `/api/v1/admin/credits/requests` | `GET /`, `POST /{id}/approve`, `POST /{id}/reject`, `POST /cleanup/expired-quotes` |
| `audits` | `api/routes/audits.py` | `/api/v1/audit` | `POST /discover`, `POST /estimate`, `POST /run`, `GET /{id}`, `GET /` |
| `analyses` | `api/routes/analyses.py` | `/api/v1` | `POST /analyze/estimate`, `GET /analyses`, `GET /analyses/{id}`, `POST /analyze/{type}` |

### Service Layer

| Service | File | Responsibility |
|---------|------|----------------|
| `auth.py` | `api/services/auth.py` | WorkOS JWT verification, JWKS caching (15min TTL), user sync to Supabase |
| `supabase.py` | `api/services/supabase.py` | Singleton Supabase client with reset capability |
| `analyses.py` | `api/services/analyses.py` | Proxy to SDK Worker with tenacity retry, credit flow |
| `audits.py` | `api/services/audits.py` | Quote lifecycle (create→validate→claim→deduct→refund→record→submit) |
| `credits.py` | `api/services/credits.py` | Tiered pricing calculations, credit deduction |
| `credit_requests.py` | `api/services/credit_requests.py` | Manual payment flow with invoice generation |
| `cloud_tasks.py` | `api/services/cloud_tasks.py` | GCP Cloud Tasks v2 HTTP task creation |
| `email.py` | `api/services/email.py` | SendGrid transactional emails singleton |

### Pydantic Models

| File | Models |
|------|--------|
| `api/models/common.py` | `HealthResponse` |
| `api/models/credits.py` | `CreditBalanceResponse`, `CreditHistoryResponse`, `CreditHistoryItem` |
| `api/models/credit_requests.py` | `CreditRequestCreate`, `CreditRequestResponse`, `CreditRequestList`, `PaymentProofUpload`, `AdminApproval`, `AdminRejection` |
| `api/models/audits.py` | `EstimateRequest`, `DiscoveryRequest`, `AuditRunRequest`, `AuditResponse`, `AuditListResponse` |
| `api/models/analyses.py` | `AnalyzeRequest`, `AnalysisEstimateRequest`, `AnalysisEstimateResponse`, `AnalysisResponse`, `AnalysisListResponse`, `AnalysisStatus` |

### Auth Flow

```
1. Client sends Bearer JWT (from WorkOS session)
2. get_current_user() dependency extracts token
3. verify_token() in auth.py:
   a. Decode JWT header → get kid
   b. Fetch JWKS (cached 15 min, async lock)
   c. Verify RS256 signature
   d. Validate: iss (api.workos.com), aud (config), exp
4. sync_user_to_supabase():
   a. Upsert into users table (id, email, first_name, last_name)
   b. Upsert into organizations table (if org_id present)
   c. Set user.organization_id
5. Return user dict → injected into route handler
```

### Internal Auth

Internal endpoints (health cleanup, worker callbacks) use `X-Internal-Secret` header validated via `get_internal_secret()` dependency. The secret value is configurable via environment variable.

### Rate Limiting

- `RateLimiter` class with Redis (distributed) or in-memory fallback
- Default: 100 req/min
- Audit estimate: 10 req/min
- Audit run: 30 req/min
- Credit purchase: 5 req/min
- Returns 429 with `Retry-After` and `X-RateLimit-*` headers

### Security Middleware

Applied to every response:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` (production only)
- CORS: whitelisted origins from config

### SSRF Protection (`api/utils/url_validator.py`)

Before any outbound HTTP request:
- Blocks `169.254.169.254` (AWS metadata)
- Blocks `metadata.google.internal` (GCP metadata)
- Blocks `localhost`, `127.0.0.1`, `[::1]`
- Blocks all private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Blocks IPv6 private, link-local, multicast, loopback
- Allows only `http`/`https` schemes, ports 80/443

### SiteScanner (`api/scanner/site.py`)

URL discovery for site audits:
- Reads robots.txt
- Parses XML sitemaps (including sitemap indexes, max 10 sub-sitemaps)
- Extracts homepage links
- Excludes admin paths (wp-admin, admin, api, login, cart, checkout)
- Limits: 10MB content size, 10,000 sitemap URLs

### Credit Flow — End to End

```
1. Estimate: POST /audit/estimate
   → Create pending_audits record (status=pending, 30min TTL)
   → Return quote_id + credits_required

2. Run: POST /audit/run with quote_id
   → validate_and_claim_quote() — atomic pending→processing
   → deduct_credits() — PostgreSQL FOR UPDATE
   → Create audits record (status=queued)
   → Submit to Cloud Tasks → SDK Worker
   → On failure: refund_credits() + update status=failed

3. Worker completes:
   → SDK Worker writes results to audit_tasks
   → DB trigger notifies Gateway via LISTEN/NOTIFY
   → Gateway pushes to frontend via WebSocket

4. Frontend receives real-time updates:
   WebSocket connection receives push events → TanStack Query cache updated
```

### DEV_MODE

When `DEV_MODE=true`:
- Credit balance always returns 999,999
- Credit deductions are skipped
- Blocked from production by config validator
