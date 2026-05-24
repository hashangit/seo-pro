# 10 — Architectural Findings

## Overview

This document captures observations, patterns, and potential gaps identified during the comprehensive architecture review. Items are categorized by severity and type. Resolved items are marked with ✓ and a resolution date.

---

## Strengths

### Security

- **Multi-layer SSRF protection**: URL validator blocks all private/internal IPs, validated before any outbound HTTP request
- **Atomic credit operations**: PostgreSQL `FOR UPDATE` row locks prevent race conditions on credit balances
- **Row-Level Security**: All 7 tables have per-user RLS policies + service role bypass
- **JWT verification**: WorkOS JWKS cached with thread-safe async lock, 15-min TTL
- **CORS**: Explicit whitelist, not wildcard
- **Security headers**: X-Frame-Options, X-Content-Type-Options, XSS-Protection, HSTS
- **Non-root containers**: All Dockerfiles run as non-root user
- **Secret Management**: Google Secret Manager for all production secrets
- **Input validation**: Control character stripping, length limits, MIME type validation

### Architecture

- **Code reuse across CLI and cloud**: Same skills/ and agents/ files used locally and in Cloud Run
- **Compensating transactions**: Credit refund on worker failure
- **Idempotency**: Audit submission supports idempotency_key
- **Graceful degradation**: Development falls back to basic scraping when SDK unavailable
- **Retry logic**: Tenacity-based exponential backoff on worker calls
- **DEV_MODE gate**: Clear separation between dev/testing and production

### Observability

- **Structured logging**: Python `logging` with `extra` fields for context
- **CI scanning**: Trivy vulnerability scanner in CI pipeline
- **Health checks**: Both /health and /health/ready endpoints with dependency checks

---

## Architectural Observations

### 0. Analysis Flow Fragmentation (High) — OPEN

The SaaS analysis flow currently mixes two domain concepts: quote/request lifecycle and paid job/result lifecycle. Site audits have quote records (`pending_audits`) and async Cloud Task execution (`audits`), while individual analyses and page audits bypass durable quotes and run through synchronous worker proxy calls into `analyses`.

This creates several product and engineering gaps:

- Individual/page analysis cannot survive insufficient credits and later top-up.
- Credit requests are not linked to the quote/request that caused the top-up need.
- Site audits route through `/audit/{id}` while individual/page analyses route through `/analysis/{id}`.
- Worker result persistence is split across `audits` and `analyses`.
- Some frontend/API result contracts are inconsistent.

**Target direction:** Separate quote/request records from paid analysis job/result records. All modes should follow quote -> accept -> credit gate -> async Cloud Task -> worker-isolated `analysis_id` -> `/analysis/{analysis_id}`. See [../ANALYSIS_FLOW_ARCHITECTURE.md](../ANALYSIS_FLOW_ARCHITECTURE.md) and [11-analysis-flow-current-and-target.md](./11-analysis-flow-current-and-target.md).

### 1. Dual Orchestration Paths (Medium) — ✓ RESOLVED (2026-05-23)

~~The system has **two different audit orchestration paths**:~~

~~| Path | Entry Point | Mechanism | State |~~
~~|------|-------------|-----------|-------|~~
~~| API Gateway | `api/routes/analyses.py` | `cloud_tasks.py` → SDK Worker directly | Active |~~
~~| Orchestrator | `orchestrator/scheduler.py` | Cloud Tasks → HTTP_WORKER_URL / BROWSER_WORKER_URL | Legacy |~~

~~The orchestrator references `HTTP_WORKER_URL` and `BROWSER_WORKER_URL` which don't exist — there's only a unified SDK Worker. The API layer bypasses the orchestrator entirely. The orchestrator is bundled in the Gateway Docker image but doesn't appear to be actively used.~~

**Resolution**: The legacy orchestrator (`orchestrator/scheduler.py`) has been completely removed along with `deploy/Dockerfile.orchestrator`, `HTTP_WORKER_URL`, and `BROWSER_WORKER_URL`. Site-audit orchestration now flows through API Gateway → Cloud Tasks → SDK Worker; individual/page analysis still has a direct synchronous Gateway → SDK Worker path tracked under Finding #0. The Dockerfile.gateway no longer copies any orchestrator code.

### 2. In-Memory State in Orchestrator (Low) — ✓ RESOLVED (2026-05-23)

~~The orchestrator uses `_audit_state = {}` (a plain Python dict) to track in-flight audits. If the Cloud Run instance restarts or scales, this state is lost. The database has ground truth (tasks + audits), but the completion-detection logic counting from in-memory state would break.~~

**Resolution**: Removed with the orchestrator. All state is now in Supabase tables (`audits`, `audit_tasks`, `analyses`). No in-memory tracking exists anywhere in the system.

### 3. Worker Writes to DB Directly + Callback (Low) — ✓ RESOLVED (2026-05-23)

~~The SDK Worker writes results directly to `audit_tasks` in Supabase AND can optionally POST to the orchestrator's `/task-update` endpoint. This dual-path result reporting is partially redundant.~~

**Resolution**: No `/task-update` endpoint exists anymore. The SDK Worker writes results exclusively to Supabase tables. Single source of truth.

### 4. No WebSocket/SSE for Real-Time Updates (Low) — ✓ RESOLVED (2026-05-23)

~~The earlier audit status path used repeated HTTP status checks. For a platform with scale-to-zero workers, that was pragmatic, but for large audits with many pages it created unnecessary load. WebSocket or Server-Sent Events could reduce this.~~

**Resolution**: WebSocket + Postgres LISTEN/NOTIFY replaces HTTP polling. Architecture:

```
Worker writes to Supabase
  → DB trigger: pg_notify('audit_changes', payload)
    → FastAPI Gateway: asyncpg LISTEN on WebSocket connect
      → wss://gateway sends events to frontend
        → TanStack Query cache updated via setQueryData
```

New files: `api/routes/ws.py`, `api/core/ws_auth.py`, `frontend/hooks/use-audit-stream.ts`; the LISTEN/NOTIFY trigger is consolidated into `supabase/migrations/001_initial_schema.sql`. This resolved the original audit polling gap, but the broader analysis-flow tracker still owns any remaining polling/fallback behavior and the move to analysis-centered realtime events. WorkOS remains the sole auth system (JWT passed as WebSocket query parameter).

### 5. No Global State Management in Frontend (Neutral) — ✓ RESOLVED (2026-05-23)

~~The frontend uses no state management library — purely React `useState`/`useEffect` plus WorkOS auth hooks. This keeps things simple and works well for the current feature set. Only worth reconsidering if the app grows significantly more complex.~~

**Resolution**: TanStack Query (`@tanstack/react-query`) added as the standard data-fetching and server-state layer. Provides:
- Query deduplication (e.g., `CreditBalance` header and `CreditsHistoryPage` share a cache)
- Declarative `refetchInterval` for polling (conditional, auto-stops on completion)
- Mutation-based operations with automatic cache invalidation
- Standardized loading/error states across all components

Custom hooks in `frontend/hooks/use-queries.ts` wrap all `lib/api.ts` functions. No global store is needed for local/UI state — `useState` remains appropriate for form state, dialog state, etc.

### 6. Payment Gateway Pending (Medium)

The credit purchase flow uses a manual payment process (request → invoice → proof upload → admin approval). The README and code comments reference an impending IPG (International Payment Gateway) integration to replace this. This is a known and tracked gap.

### 7. Supabase JS Client Unused in Frontend (Low) — ✓ RESOLVED (2026-05-23)

~~The frontend has `lib/supabase.ts` with a Supabase JS client and TypeScript type definitions, but all data access goes through the FastAPI backend. The Supabase client appears to be set up but not actively used in components.~~

**Resolution**: `frontend/lib/supabase.ts` deleted. `@supabase/supabase-js` removed from frontend dependencies. Supabase env vars (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`) removed from `docker-compose.yml` and `docs/DEPLOYMENT.md`. All data access is routed exclusively through FastAPI.

### 8. Docker Compose References Legacy HTTP Worker (Low) — ✓ RESOLVED (2026-05-23)

~~`docker-compose.yml` includes an `http-worker` service that builds `Dockerfile.http-worker`, but no such Dockerfile exists in `deploy/`. This service targets the old worker architecture.~~

**Resolution**: The `http-worker` service was already removed from `docker-compose.yml` in the prior cleanup. Only `gateway` and `frontend` services remain.

### 9. No Dedicated Test Suite for Workers (Low)

The CI pipeline runs `pytest api/` which covers the gateway. The SDK worker (`workers/sdk_worker.py`) doesn't have dedicated test coverage.

### 10. Cloud Build vs GitHub Actions Overlap (Low) — ✓ RESOLVED (2026-05-23)

~~Both `cloudbuild.yaml` (GCP Cloud Build) and `.github/workflows/ci.yml` (GitHub Actions) exist. The CI file runs tests/lints/builds, while Cloud Build handles production deployments. This is standard but worth noting that there are two CI systems in play.~~

**Resolution**: The two pipelines serve complementary purposes:
- **ci.yml** (GitHub Actions): CI layer — tests, lint, typecheck, security scanning (Trivy), Docker build smoke tests (no push). Runs on PRs.
- **cloudbuild.yaml** (Cloud Build): CD layer — builds, pushes to Artifact Registry, deploys to Cloud Run. Runs on push to main.

Overlap is limited to Docker image builds (ci.yml verifies the build, cloudbuild.yaml deploys it). The stale orchestrator build step was removed from ci.yml (`ruff check orchestrator/` and `Dockerfile.orchestrator` build).

---

## Potential Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Z.AI API downtime | Low | High | No fallback in production (returns 503) |
| Secret Manager access issues | Low | Critical | Deployments fail without secrets |
| WorkOS JWT validation failure | Low | High | Users can't authenticate |
| Cloud Tasks delivery failure | Low | Medium | 3 retries with backoff + dead-letter queue |
| SendGrid rate limit / block | Low | Medium | Falls back to logging |

---

## Directory / File Notes

### Empty or Minimal Directories

- `.commandcode/taste/` — Now populated with learned preferences (architecture: route through FastAPI, real-time: use LISTEN/NOTIFY)
- `.commandcode/plan/` — Contains implementation plans (e.g., `cleanup-findings-5-7-10.md`)
- `docs/plans/` — Contains planning documents
- `pdf/` — Single reference file, could be consolidated into `seo/references/`

### Files Removed Since Review

- `orchestrator/scheduler.py` — Legacy orchestrator with in-memory state (removed 2026-05-23)
- `deploy/Dockerfile.orchestrator` — No longer needed (removed 2026-05-23)
- `frontend/lib/supabase.ts` — Dead Supabase client (removed 2026-05-23)
- `frontend/lib/api-client.ts` — Unused server-side API client, superseded by `lib/api.ts` (removed 2026-05-23)
- `deploy/Dockerfile.http-worker` — Never existed (legacy reference already removed from docker-compose)

### Documentation Files Present

11 documentation files in `docs/`:
- Operational: ARCHITECTURE, DEPLOYMENT, DEVELOPER_GUIDE, LOCAL_DEVELOPMENT
- Feature: FEATURES, COMMANDS, MCP-INTEGRATION
- User: INSTALLATION, TROUBLESHOOTING
- Technical: RATE-LIMITING, TODO

---

## Summary of Resolutions

| Finding | Status | Resolution Date |
|---------|--------|----------------|
| 1. Dual Orchestration Paths | ✓ Resolved | 2026-05-23 |
| 2. In-Memory State | ✓ Resolved | 2026-05-23 |
| 3. Worker Dual-Result Reporting | ✓ Resolved | 2026-05-23 |
| 4. No Real-Time Updates | ✓ Resolved | 2026-05-23 |
| 5. No Global State Management | ✓ Resolved | 2026-05-23 |
| 6. Payment Gateway Pending | Open | — |
| 7. Supabase Client Unused | ✓ Resolved | 2026-05-23 |
| 8. Legacy HTTP Worker Reference | ✓ Resolved | 2026-05-23 |
| 9. No Worker Test Suite | Open | — |
| 10. CI/CD Overlap | ✓ Resolved | 2026-05-23 |

### Open Items

- **#0 Analysis Flow Fragmentation**: High-priority architecture cleanup. Use the dedicated analysis flow tracker before changing quote, audit, analysis, credit, worker, or result-route code.
- **#6 Payment Gateway**: Manual payment flow (request → invoice → proof → admin approval) is functional but manual. IPG integration would automate this. Known and tracked gap.
- **#9 Worker Test Suite**: The SDK worker has no dedicated tests. Gateway tests (`pytest api/`) exist. Worth adding worker integration tests as the system grows.
