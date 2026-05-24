# Analysis Flow Architecture

**Status:** Target-state design and migration tracker
**Last updated:** 2026-05-24

This document records the current analysis/audit implementation, the known gaps, and the intended architecture. Keep it current as implementation moves from the current state to the target state.

## Executive Summary

The product should treat every user-submitted SEO job as a saved quote/request first, then as a paid analysis job only after the credit gate passes. Quotes and analysis jobs are related but not the same thing:

- **Quote/request:** The saved user intent, price, selected scope, expiry/reminder state, and credit shortfall state.
- **Analysis job/result:** The paid execution record, worker status, final results, and refund/error state.

The current code partially implements this model for site audits only. Individual analyses and page audits skip the quote lifecycle, deduct credits directly, and synchronously proxy to the worker. This creates inconsistent behavior, timeout risk, weak top-up recovery, and fragmented result routes.

## Current Implemented State

### Data Model

| Table | Current purpose | Notes |
|---|---|---|
| `pending_audits` | Site-audit quote records | Only site audits create durable quotes today. Quotes expire after 30 minutes and are currently cleanup targets, which conflicts with abandoned-cart reminders. |
| `audits` | Full-site audit job/results | Site audits run through Cloud Tasks and store results here. |
| `audit_tasks` | Subtask progress for site audits | References `audits`; not used by individual/page analysis. |
| `analyses` | Individual and page-audit job/results | Has `analysis_mode` values for `individual`, `page_audit`, and `site_audit`, but site audits do not actually use it. |
| `credit_requests` | Manual top-up/payment flow | Not linked to a quote or intended analysis today. |
| `credit_transactions` | Credit ledger | Spend/refund/purchase records; individual/page spends currently lack a useful analysis reference ID in some paths. |

### Runtime Flows

| Flow | Quote? | Credit gate | Execution | Result route | Result table |
|---|---:|---|---|---|---|
| Individual analysis | No | Direct `deduct_credits` call | Synchronous API-to-worker proxy | `/analysis/{analysis_id}` | `analyses` |
| Page audit | No | Direct `deduct_credits` call | Synchronous API-to-worker proxy | Intended `/analysis/{analysis_id}` | `analyses` |
| Site audit | Yes, `pending_audits` | Quote claim, then `deduct_credits` | Async Cloud Tasks | `/audit/{audit_id}` | `audits` |
| Credit top-up | N/A | Admin approval adds credits | Manual payment proof flow | `/credits/requests` | `credit_requests` |

### Inferred Original Intent

The documentation and review notes indicate the intended platform shape was:

1. FastAPI Gateway authenticates users, handles credits, and submits jobs.
2. Cloud Tasks dispatches work to the SDK Worker.
3. SDK Worker starts an isolated Claude Agent SDK run and writes results to Supabase.
4. Frontend observes status through FastAPI and WebSocket updates.

The current code honors that async path for site audits, but individual analyses and page audits still use synchronous proxy calls.

## Current Gaps And Bugs

### Product Flow Gaps

- Quotes exist only for site audits, so individual/page analysis cannot be resumed after insufficient credits or top-up.
- Credit requests are not linked to the quote/request that caused the top-up need.
- Expired quotes are deleted instead of retained for product analytics, reminders, and user recovery.
- There is no lifecycle state for `awaiting_credits`, `accepted`, `abandoned`, `converted`, or `superseded`.
- Manual top-up approval does not automatically re-check saved quotes or continue an accepted analysis request.

### Execution Gaps

- Individual/page analysis runs synchronously and can timeout.
- Worker result persistence is split: worker writes site audit results to `audits`, while API writes individual/page analysis results to `analyses`.
- Site audit tasks do not use the `analyses` table despite `analysis_mode='site_audit'` existing.
- Worker task payloads do not consistently carry `analysis_id`, `user_id`, selected URLs, selected analysis types, quote ID, and correlation metadata.
- There is no single worker update contract for all analysis modes.

### Frontend/API Bugs

- Individual analysis UI estimates all selected types but currently runs only the first selected type.
- Page audit creates an analysis record but does not consistently return `analysis_id`.
- Analysis status API returns `results`, while the frontend result page expects `results_json`.
- `/analysis/{id}` uses the analysis stream hook, but the WebSocket trigger/channel is currently audit-centered.
- Site audit result route is `/audit/{id}`, while individual/page analysis route is `/analysis/{id}`.

### Credit/Ledger Gaps

- Individual/page analysis deducts before the analysis ID is reliably available as the ledger reference.
- There is no quote-level record of `balance_at_quote`, `credits_required`, `credits_shortfall`, `accepted_at`, or top-up continuation state.
- Refund and failure behavior is implemented inconsistently across individual/page/site flows.

## Intended Architecture

### Domain Model

Use two core concepts:

1. **Analysis Quote**
   - Durable record of requested work before execution.
   - Stores user, email, URL, mode, selected analysis types, selected URLs, pricing, quote expiry, credit shortfall, reminder eligibility, and accepted state.
   - Can exist without enough credits.
   - Can be linked to a credit request.

2. **Analysis Job**
   - Paid execution spawned from a quote after the credit gate passes.
   - Stores status, worker run metadata, results, errors, refund state, and completion timestamps.
   - Public result route is `/analysis/{analysis_id}` for every mode.

### Target User Flow

```text
User configures analysis
  -> estimate creates or updates an analysis quote
  -> user accepts quote
  -> backend checks balance
    -> enough credits:
       deduct credits with reference_id = analysis_id
       create/enqueue analysis job
       route user to /analysis/{analysis_id}
    -> insufficient credits:
       mark quote awaiting_credits
       show shortfall and top-up action
       optionally create/link credit_request
       after credit approval, re-check balance
         -> enough credits: create/enqueue analysis job
         -> still short: keep awaiting_credits and notify user
```

### Target Backend Flow

```text
POST /api/v1/analysis-quotes
  validates request, discovers URLs where needed, prices scope, stores quote

POST /api/v1/analysis-quotes/{quote_id}/accept
  checks ownership, expiry, selected scope, and balance
  if insufficient: records shortfall and returns top-up required response
  if sufficient: creates analysis job, deducts credits, enqueues Cloud Task

Cloud Tasks -> SDK Worker
  payload includes analysis_id, quote_id, user_id, mode, types, urls, root url
  worker starts one isolated agent session for that analysis_id
  worker writes status/results/errors to the analysis job record

GET /api/v1/analyses/{analysis_id}
  returns one normalized status/result shape for every mode
```

### Target Database Shape

The exact migration can be refined during implementation, but the target needs these concepts:

| Concept | Recommended table | Key fields |
|---|---|---|
| Quote/request | `analysis_quotes` | `id`, `user_id`, `email`, `url`, `analysis_mode`, `analysis_types`, `selected_urls`, `credits_required`, `balance_at_quote`, `credits_shortfall`, `status`, `expires_at`, `accepted_at`, `converted_analysis_id`, `metadata` |
| Job/result | `analyses` | `id`, `quote_id`, `user_id`, `url`, `analysis_mode`, `analysis_types`, `selected_urls`, `status`, `credits_used`, `results_json`, `error_message`, `worker_run_id`, `started_at`, `completed_at`, `metadata` |
| Top-up link | `credit_requests` extension | `quote_id`, optional `analysis_id`, `credits_requested`, `status` |
| Ledger | `credit_transactions` | Use `reference_id = analysis_id` and `reference_type = 'analysis'` for all paid analysis spend/refund entries. |

### Target Result Routing

All paid jobs should use:

```text
/analysis/{analysis_id}
```

The current `/audit/{audit_id}` route should not be preserved as a product architecture requirement. During migration it can be removed or redirected, depending on whether there is production data to preserve.

### Target Worker Contract

All modes should enqueue the same kind of task:

```json
{
  "analysis_id": "uuid",
  "quote_id": "uuid",
  "user_id": "workos_user_id",
  "url": "https://example.com",
  "analysis_mode": "individual | page_audit | site_audit",
  "analysis_types": ["technical", "content"],
  "selected_urls": ["https://example.com/page"],
  "requested_at": "iso-8601",
  "correlation_id": "string"
}
```

The worker must treat `analysis_id` as the isolation boundary. A worker run may spawn agent/subagent sessions internally, but every status update and final result belongs to exactly one `analysis_id`.

## Migration Strategy

Do not rewrite the system in one pass. Move through small, verifiable stages.

### Phase 0: Document And Stabilize

- [x] Document current state, bugs, and target architecture.
- [ ] Fix immediate user-visible bugs without changing the domain model.
- [ ] Add tests that pin the current expected behavior before refactoring.

### Phase 1: Quote Model

- [ ] Add generalized analysis quote model.
- [ ] Create quote endpoints for all three modes.
- [ ] Store quote state for insufficient credit and accepted-but-not-paid flows.
- [ ] Link credit requests to quotes.

### Phase 2: Unified Async Execution

- [ ] Make individual analysis enqueue Cloud Tasks.
- [ ] Make page audit enqueue Cloud Tasks.
- [ ] Worker updates `analyses` directly by `analysis_id`.
- [ ] Normalize status/result API shape.

### Phase 3: Site Audit Migration

- [ ] Move site audit paid jobs from `audits` to `analyses`.
- [ ] Replace `/audit/{id}` navigation with `/analysis/{id}`.
- [ ] Remove or redirect legacy audit routes.

### Phase 4: Cleanup And Product Recovery

- [ ] Retain abandoned/expired quotes instead of deleting them.
- [ ] Add reminder eligibility fields and reminder jobs.
- [ ] Add stale job detection and refund/recovery policy.
- [ ] Remove obsolete tables/routes after migration is complete.

## Progress Tracker

| Area | Current state | Target state | Status |
|---|---|---|---|
| Quote persistence | Site audit only via `pending_audits` | All modes via generalized quote model | Not started |
| Insufficient credit flow | API returns 402; no saved recovery for individual/page | Quote enters `awaiting_credits`, top-up can resume | Not started |
| Credit request link | Standalone payment request | Credit request can link to quote | Not started |
| Execution | Individual/page sync, site async | All modes async via Cloud Tasks | Not started |
| Result route | `/analysis/{id}` and `/audit/{id}` | `/analysis/{id}` for all paid jobs | Not started |
| Result persistence | Split across `analyses` and `audits` | Paid jobs persist in `analyses` | Not started |
| Worker update contract | Site audit writes `audits`; individual/page return to API | Worker writes all jobs by `analysis_id` | Not started |
| Realtime status | Audit-centered LISTEN/NOTIFY | Analysis-centered status events | Not started |
| Legacy audit model | Active | Removed, not preserved | Not started |

## Non-Goals

- Do not preserve legacy `/audit/{id}` as a permanent user-facing architecture.
- Do not put unpaid quotes, paid jobs, credit requests, and final reports into one overloaded table.
- Do not let the frontend talk directly to Supabase.
- Do not run agent analysis inside the main API gateway.
- Do not rely on synchronous worker proxy calls for paid jobs.

