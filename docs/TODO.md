# TODO — SEO Pro

## Deferred from February 2026 Research Report

Items identified during the Feb 2026 SEO research audit that require additional implementation work.

- [ ] **Fake freshness detection** (Priority: Medium)
  Compare visible dates (`datePublished`, `dateModified`) against actual content modification signals.
  Flag pages with updated dates but unchanged body content. This is a spam pattern Google targets.

- [ ] **Mobile content parity check** (Priority: Medium)
  Compare mobile vs desktop meta tags, structured data presence, and content completeness.
  Flag discrepancies that could affect mobile-first indexing. Currently only viewport/touch targets
  are checked, not content equivalence.

- [ ] **Discover optimization checks** (Priority: Low-Medium)
  Clickbait title detection, content depth scoring, local relevance signals, sensationalism flags.
  Relevant to Feb 2026 Discover Core Update which emphasizes original reporting and E-E-A-T signals.

- [ ] **Brand mention analysis Python implementation** (Priority: Low)
  Currently documented in `seo-geo/SKILL.md` but no programmatic scoring. Consider implementing
  a check that searches for brand entity presence signals (unlinked mentions, co-citation patterns,
  entity authority indicators).

---

## Infrastructure Improvements (From Architecture Review - Feb 2026)

- [ ] **Dead Letter Queue for Cloud Tasks** (Priority: Medium)
  Configure Cloud Tasks dead letter queue for failed audit tasks.
  Currently failed tasks are abandoned after retries with no recovery mechanism.
  Requires: DLQ configuration in Cloud Tasks, monitoring/alerting for DLQ depth,
  replay mechanism for failed tasks.

- [x] **Real-time audit updates via WebSockets** (Priority: Low) — ~~DONE (2026-05-23)~~
  Replaced 2-second polling with WebSocket + Postgres LISTEN/NOTIFY.
  See `api/routes/ws.py`, `frontend/hooks/use-audit-stream.ts`, `supabase/migrations/002_audit_change_trigger.sql`.

- [x] ~~**Research: In-memory orchestrator state persistence** (Priority: Low)~~ — NO LONGER RELEVANT
  Legacy orchestrator (`orchestrator/scheduler.py`) has been completely removed (2026-05-23).
  All state is now in Supabase tables. No in-memory state exists anywhere in the system.

---

## Code Quality Improvements (From Architecture Review - Feb 2026)

Non-critical improvements identified during architectural assessment. None are blocking.

### Backend (Python/FastAPI)

- [ ] **Replace singleton pattern with dependency injection** (Priority: Low)
  Current: Global `_supabase_client` and `_settings` singletons in `api/services/supabase.py`
  and `api/config.py` create hidden dependencies and make testing harder.
  Recommendation: Use FastAPI's `Depends()` for cleaner dependency injection.
  Impact: Code maintainability, testability. No functional impact.

- [x] ~~**Remove deprecated worker configuration** (Priority: Low)~~ — DONE (2026-05-23)
  `HTTP_WORKER_URL`, `BROWSER_WORKER_URL`, and `ORCHESTRATOR_URL` removed from `api/config.py`.
  Legacy orchestrator (`orchestrator/scheduler.py`) completely removed.
  Files: `api/config.py`, `deploy/Dockerfile.orchestrator` (deleted)

- [ ] **Add request correlation IDs for tracing** (Priority: Medium)
  Add unique request IDs to API logs for debugging distributed requests.
  Frontend sends `X-Request-ID` header (already in CORS allow_headers).
  Backend should generate if not present and include in all log statements.
  Impact: Debugging production issues faster.

- [ ] **Add timeout mechanism for stuck analyses** (Priority: Medium)
  Analyses in "processing" state with no update after X minutes should be
  marked as failed with automatic credit refund.
  Requires: Scheduled job (Cloud Scheduler) or DB trigger to detect stale records.
  Impact: Prevents credits being locked indefinitely on stuck jobs.

- [ ] **Use Jinja2 templates for email HTML** (Priority: Low)
  Current: HTML email templates are hardcoded as large f-strings in `api/services/email.py`.
  Recommendation: Use Jinja2 templating engine with separate `.html` template files.
  Benefits: Better separation of concerns, easier maintenance, cleaner code.
  Impact: Code maintainability. No functional impact.

### Frontend (Next.js/TypeScript)

- [x] ~~**Consider React Query for API data fetching** (Priority: Low)~~ — DONE (2026-05-23)
  TanStack Query (`@tanstack/react-query`) implemented as the standard data-fetching layer.
  See `frontend/hooks/use-queries.ts`, `frontend/lib/query-client.ts`, `frontend/components/providers.tsx`.

- [ ] **Improve token refresh strategy** (Priority: Low)
  Current: 60-second polling interval for token refresh.
  Better: Use token expiration time and refresh proactively before expiry.
  Impact: More robust auth, handles inactive tabs better.

### Database

- [ ] **Add index for stale analyses query** (Priority: Low)
  If implementing timeout mechanism, add index for:
  `CREATE INDEX idx_analyses_stale ON analyses(status, updated_at) WHERE status = 'processing';`

---

## Architecture Decisions Documented (Feb 2026)

These are intentional design decisions, not TODOs:

- **Worker → Database communication**: SDK Worker writes directly to Supabase, not via API.
  This reduces latency and avoids API becoming a bottleneck. Both API and Worker share
  the same database schema.

- **Credit refund on failure**: Implemented via `refund_credits` RPC in `analyses.py`.
  Automatic refund when worker returns error or throws exception.

- **Manual payment flow**: Using credit request system with admin approval.
  PayHere integration exists but not active. Intentional for early-stage operations.

- **Rate limiting**: Implemented at `api/rate_limiter.py` with Redis (primary) and
  in-memory (fallback). Per-endpoint limits configured in `RATE_LIMITS` dict.

---

*Last updated: 2026-05-23*
