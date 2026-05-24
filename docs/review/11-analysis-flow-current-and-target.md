# 11 — Analysis Flow Current And Target State

**Date:** 2026-05-24
**Status:** Active architecture tracker

This review note captures the current implementation, known gaps, and intended direction for the SaaS analysis flow. The implementation tracker lives in [../ANALYSIS_FLOW_ARCHITECTURE.md](../ANALYSIS_FLOW_ARCHITECTURE.md).

## Current State

The current system has two partially overlapping domains:

- `analyses`: individual analysis and full-page audit result tracking.
- `audits`: full-site audit result tracking.

It also has a quote concept, but only for site audits:

- `pending_audits`: quote records created by site-audit estimate flows.

Credit purchases are independent:

- `credit_requests`: manual top-up requests with proof upload and admin approval.

This means the product currently has quote persistence for site audits, but not for individual/page analysis. The result path is also split between `/analysis/{id}` and `/audit/{id}`.

## Current Flow Matrix

| Flow | Quote table | Job table | Execution | Route | Main issue |
|---|---|---|---|---|---|
| Individual | None | `analyses` | Synchronous worker proxy | `/analysis/{id}` | Cannot survive top-up; timeout risk |
| Page audit | None | `analyses` | Synchronous worker proxy | `/analysis/{id}` intended | Missing/fragile `analysis_id` return |
| Site audit | `pending_audits` | `audits` | Cloud Tasks | `/audit/{id}` | Diverges from analysis model |
| Credit top-up | None | `credit_requests` | Manual admin approval | `/credits/requests` | Not linked to requested work |

## Known Bugs

- Individual analysis can estimate multiple selected types but runs only the first selected type.
- Page audit can create an `analyses` row without returning the analysis ID needed by the frontend.
- Analysis status response and frontend disagree on the result field name (`results` vs `results_json`).
- Analysis WebSocket hook is wired as if analyses have realtime events, while the database notification path is audit-centered.
- Individual/page analysis spend entries do not consistently reference the created analysis job.

## Architectural Gaps

- No general quote model for all modes.
- No saved `awaiting_credits` state for accepted quotes with insufficient balance.
- No link from a top-up request back to the quote that caused it.
- Expired quotes are cleanup targets rather than retained records for reminders and analytics.
- Paid job execution is split between synchronous API calls and async Cloud Tasks.
- Worker result persistence is split between API-updated `analyses` and worker-updated `audits`.
- Site audits do not use `analysis_mode='site_audit'` despite the database allowing it.

## Intended Model

The target architecture has two core concepts:

1. **Analysis quote/request**
   A durable, unpaid or pre-paid record of user intent. It stores requested scope, price, expiry, selected URLs, selected analysis types, user email, balance at quote time, shortfall, and reminder/conversion state.

2. **Analysis job/result**
   A paid execution record created only after the credit gate passes. It stores worker status, credits used, result JSON, error/refund state, and completion timestamps.

Every paid analysis mode should eventually use:

```text
/analysis/{analysis_id}
```

The `/audit/{id}` route and `audits` table are not target-state architecture.

## Intended Flow

```text
Create or update quote
  -> user accepts quote
  -> check balance
    -> sufficient:
       create analysis job
       deduct credits with analysis_id as ledger reference
       enqueue Cloud Task
       send user to /analysis/{analysis_id}
    -> insufficient:
       mark quote awaiting_credits
       show shortfall and top-up path
       link credit request to quote
       after top-up approval, re-check balance and continue if sufficient
```

## Target Components

| Component | Target responsibility |
|---|---|
| FastAPI Gateway | Auth, quote creation, credit gate, Cloud Task enqueue, public status API |
| Supabase | Durable state for quotes, jobs, credits, transactions, and realtime notifications |
| SDK Worker | Isolated analysis execution per `analysis_id`; writes status/results to Supabase |
| Frontend | Quote configuration, top-up continuation, unified `/analysis/{id}` result view |
| Email jobs | Quote reminders, top-up continuation notices, completion/failure notices |

## Migration Direction

1. Fix immediate correctness bugs in current flows.
2. Add a generalized quote model for all modes.
3. Link top-up requests to quotes.
4. Move individual and page analysis execution to Cloud Tasks.
5. Make the worker update `analyses` by `analysis_id`.
6. Move site audit paid jobs from `audits` to `analyses`.
7. Remove or redirect legacy audit routes and retire obsolete tables.

## Review Status

| Question | Decision |
|---|---|
| Preserve legacy `/audit/{id}` permanently? | No |
| Use async execution for all paid analysis modes? | Yes |
| Store quotes and jobs in the same table? | No |
| Let frontend access Supabase directly? | No |
| Run agent sessions inside the gateway? | No |
| Use analysis ID as worker isolation boundary? | Yes |

