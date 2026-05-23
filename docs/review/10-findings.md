# 10 — Architectural Findings

## Overview

This document captures observations, patterns, and potential gaps identified during the comprehensive architecture review. Items are categorized by severity and type.

---

## Strengths

### Security

- **Multi-layer SSRF protection**: URL validator blocks all private/internal IPs, validated before any outbound HTTP request
- **Atomic credit operations**: PostgreSQL `FOR UPDATE` row locks prevent race conditions on credit balances
- **Row-Level Security**: All 7 tables have per-user RLS policies + service role bypass
- **JWT verification**: WorkOS JWKS cached with thread-safe async lock, 15-min TTL
- **CORS**: Explicit whitelist, not wildcard
- **Security headers**: X-Frame-Options, X-Content-Type-Options, XSS-Protection, HSTS
- **Non-root containers**: All 3 Dockerfiles run as non-root user
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

### 1. Dual Orchestration Paths (Medium)

The system has **two different audit orchestration paths**:

| Path | Entry Point | Mechanism | State |
|------|-------------|-----------|-------|
| API Gateway | `api/routes/analyses.py` | `cloud_tasks.py` → SDK Worker directly | Active |
| Orchestrator | `orchestrator/scheduler.py` | Cloud Tasks → HTTP_WORKER_URL / BROWSER_WORKER_URL | Legacy |

The orchestrator references `HTTP_WORKER_URL` and `BROWSER_WORKER_URL` which don't exist — there's only a unified SDK Worker. The API layer bypasses the orchestrator entirely. The orchestrator is bundled in the Gateway Docker image but doesn't appear to be actively used.

**Impact**: Confusion about which code path is correct. The orchestrator has in-memory state that would be lost on restart.

### 2. In-Memory State in Orchestrator (Low)

The orchestrator uses `_audit_state = {}` (a plain Python dict) to track in-flight audits. If the Cloud Run instance restarts or scales, this state is lost. The database has ground truth (tasks + audits), but the completion-detection logic counting from in-memory state would break.

### 3. Worker Writes to DB Directly + Callback (Low)

The SDK Worker writes results directly to `audit_tasks` in Supabase AND can optionally POST to the orchestrator's `/task-update` endpoint. This dual-path result reporting is partially redundant.

### 4. No WebSocket/SSE for Real-Time Updates (Low)

Frontend polls at 2-second intervals for audit status. For a platform with scale-to-zero workers, polling is pragmatic, but for large audits with many pages, this creates unnecessary load. WebSocket or Server-Sent Events could reduce this.

### 5. No Global State Management in Frontend (Neutral)

The frontend uses no state management library — purely React `useState`/`useEffect` plus WorkOS auth hooks. This keeps things simple and works well for the current feature set. Only worth reconsidering if the app grows significantly more complex.

### 6. Payment Gateway Pending (Medium)

The credit purchase flow uses a manual payment process (request → invoice → proof upload → admin approval). The README and code comments reference an impending IPG (International Payment Gateway) integration to replace this. This is a known and tracked gap.

### 7. Supabase JS Client Unused in Frontend (Low)

The frontend has `lib/supabase.ts` with a Supabase JS client and TypeScript type definitions, but all data access goes through the FastAPI backend. The Supabase client appears to be set up but not actively used in components.

### 8. Docker Compose References Legacy HTTP Worker (Low)

`docker-compose.yml` includes an `http-worker` service that builds `Dockerfile.http-worker`, but no such Dockerfile exists in `deploy/`. This service targets the old worker architecture.

### 9. No Dedicated Test Suite for Workers (Low)

The CI pipeline runs `pytest api/` which covers the gateway. The SDK worker (`workers/sdk_worker.py`) and orchestrator (`orchestrator/scheduler.py`) don't appear to have dedicated test coverage.

### 10. Cloud Build vs GitHub Actions Overlap (Low)

Both `cloudbuild.yaml` (GCP Cloud Build) and `.github/workflows/ci.yml` (GitHub Actions) exist. The CI file runs tests/lints/builds, while Cloud Build handles production deployments. This is standard but worth noting that there are two CI systems in play.

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

- `.commandcode/taste/` — Empty (taste preferences not yet learned)
- `docs/plans/` — Contains planning documents
- `pdf/` — Single reference file, could be consolidated into `seo/references/`

### Files No Longer Referenced

- `orchestrator/scheduler.py` references `HTTP_WORKER_URL`/`BROWSER_WORKER_URL` — these env vars aren't set in any deployment config
- `docker-compose.yml` references `Dockerfile.http-worker` — file doesn't exist

### Documentation Files Present

11 documentation files in `docs/`:
- Operational: ARCHITECTURE, DEPLOYMENT, DEVELOPER_GUIDE, LOCAL_DEVELOPMENT
- Feature: FEATURES, COMMANDS, MCP-INTEGRATION
- User: INSTALLATION, TROUBLESHOOTING
- Technical: RATE-LIMITING, TODO

---

## Summary

The codebase is well-structured with clear separation of concerns. The dual-mode architecture (SaaS + CLI) is elegantly handled through shared filesystem-based skills and agents. Security is a strength with defense-in-depth across all layers. The primary areas for architectural attention are:

1. **Clean up legacy orchestrator**: Either fully integrate the orchestrator with the unified SDK worker path, or remove it and rely solely on the API gateway → Cloud Tasks → SDK Worker path
2. **Complete IPG integration**: Replace the manual payment flow with automated payment processing
3. **Remove/update legacy references**: HTTP worker Dockerfile reference in docker-compose, old worker URL references in orchestrator
4. **Consider adding worker tests**: The SDK worker currently has no dedicated test coverage
5. **Consider real-time updates**: WebSocket or SSE for audit progress instead of polling
