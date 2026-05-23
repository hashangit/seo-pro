# Plan: Findings 5, 7, 10 — State Management, Dead Code, CI Cleanup

---

## Finding 5 — Add TanStack Query + WebSocket Real-Time Architecture

**Decision:** Option A — FastAPI WebSocket + Postgres LISTEN/NOTIFY

**Rationale:** WorkOS is the only frontend auth system, FastAPI is the auth/ownership gate, and Supabase stays a backend data store. Option A matches this architecture without introducing a second frontend auth token model (WorkOS→Supabase JWT bridge) just for real-time. Option B (Supabase Realtime) requires `SUPABASE_JWT_SECRET`, a `/api/v1/auth/supabase-token` endpoint, and RLS alignment that don't exist today.

---

### Part 1: TanStack Query (shared foundation)

TanStack Query replaces manual `useState` + `useEffect` + `useRef` polling with declarative hooks. It deduplicates requests (currently `CreditBalance` in the header and `CreditsHistoryPage` both fetch `/credits/balance` independently), provides built-in caching/loading/error states, and the centralized `lib/api.ts` functions are perfect `queryFn` candidates.

**Install:** `@tanstack/react-query` (v5+ works directly with React 19)

**Create `frontend/lib/query-client.ts`** — QueryClient factory with:
- `staleTime: 30_000` for balance (avoid refetch on every mount)
- `staleTime: 5_000` for audit/analysis status
- `retry: 1` on failures

**Create `frontend/components/providers.tsx`** — wraps `QueryClientProvider` + `AuthKitProvider` together, used in root layout

**Create `frontend/hooks/use-queries.ts`** — custom hooks:
- `useCreditBalance()` — replaces `CreditBalance`'s manual fetch
- `useCreditHistory(limit?)`, `useCreditRequests(status?)`
- `useAnalysesList(limit?)`, `useAuditsList(limit?, offset?)`
- `useRunAudit()` / `useRunAnalysis()` / `usePurchaseCredits()` — mutations invalidating relevant queries
- `useAuditStatus(id)` — initial fetch from REST (fast path on page load), then WebSocket stream takes over
- `useAnalysisStatus(id)` — same pattern

**Update components:**
- `CreditBalance` → `useCreditBalance()`
- `AnalysisSelector` → `useMutation` for estimation and run
- `AnalysesListPage` → `useAnalysesList()`
- `CreditsHistoryPage` → `useCreditHistory()`, `useCreditBalance()`
- `CreditRequestsPage` → `useCreditRequests()`
- `PurchaseCredits` → `useMutation` for purchase
- `AuditPage` → `useAuditStatus(id)` + `useAuditStream(id)`
- `AnalysisResultsPage` → `useAnalysisStatus(id)` + `useAnalysisStream(id)`
- Server components (`DashboardPage`, `AuditsPage`, `AdminCreditsPage`) — prefetch via `queryClient.prefetchQuery()` in server component, hydrate to client via `HydrationBoundary`

---

### Part 2: WebSocket + Postgres LISTEN/NOTIFY

**Architecture:**
```
Worker writes to Supabase
  → DB trigger: pg_notify('audit_changes', payload)
    → FastAPI Gateway: asyncpg LISTEN on WebSocket connect
      → wss:// gateway sends events to frontend
        → queryClient.setQueryData(['audit', id], payload)
```

**Implementation:**

**1. Database trigger** (new migration: `supabase/migrations/00X_audit_change_trigger.sql`):
```sql
CREATE FUNCTION notify_audit_change()
RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('audit_changes', json_build_object(
    'id', NEW.id, 'user_id', NEW.user_id,
    'status', NEW.status, 'completed_at', NEW.completed_at,
    'page_count', NEW.page_count, 'credits_used', NEW.credits_used,
    'results_json', CASE WHEN NEW.status = 'completed'
      THEN NEW.results_json ELSE NULL END,
    'error_message', NEW.error_message
  )::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_changed AFTER UPDATE ON audits
FOR EACH ROW EXECUTE FUNCTION notify_audit_change();
```

**2. Gateway WebSocket endpoint** (`api/routes/ws.py`):
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.core.dependencies import get_user_from_ws_token

router = APIRouter()

@router.websocket("/api/v1/audit/{audit_id}/stream")
async def audit_stream(websocket: WebSocket, audit_id: str):
    user = await get_user_from_ws_token(websocket)
    await websocket.accept()

    async with settings.pg_pool.acquire() as conn:
        await conn.execute("LISTEN audit_changes")

        while True:
            try:
                notification = await asyncio.wait_for(
                    conn.get_notify(), timeout=30
                )
                payload = json.loads(notification.payload)
                if payload["user_id"] == user["id"] and payload["id"] == audit_id:
                    await websocket.send_json(payload)
                    if payload["status"] in ("completed", "failed"):
                        await websocket.close()
                        break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
            except WebSocketDisconnect:
                break
```

**3. Frontend WebSocket hook** (`frontend/hooks/use-audit-stream.ts`):
```ts
function useAuditStream(auditId: string) {
  const queryClient = useQueryClient();
  const { getAccessToken } = useAuthUser();

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    async function connect() {
      const token = await getAccessToken();
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL!.replace("https://", "wss://");
      socket = new WebSocket(`${wsUrl}/api/v1/audit/${auditId}/stream?token=${token}`);

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "ping") return;
        queryClient.setQueryData(["audit", auditId], (old) => ({
          ...(old || {}), ...data,
        }));
      };

      socket.onclose = (event) => {
        // Reconnect unless server closed cleanly (audit completed)
        if (event.code !== 1000) {
          reconnectTimer = setTimeout(connect, 2000);
        }
      };
    }

    connect();
    return () => {
      socket?.close();
      clearTimeout(reconnectTimer);
    };
  }, [auditId, queryClient, getAccessToken]);
}
```

**Why this approach:**

| Criterion | How Option A delivers |
|---|---|
| **Performance** | <100ms push from DB write to frontend — no polling interval delay |
| **Efficiency** | 1 WebSocket per audit viewer instead of ~90 HTTP requests (one every 2s for a 3-minute audit) |
| **User experience** | Instant status transitions (queued→processing→completed) instead of 2s-update flicker |
| **Cost** | 1 long Cloud Run request vs 90 short ones — roughly a wash at small scale, significant savings at scale |
| **New infrastructure** | None — LISTEN/NOTIFY is native Postgres, WebSocket is native FastAPI/browser |
| **Auth** | WorkOS JWT on WS connect — no second auth system introduced |
| **Scaling** | Per-connection overhead, but Cloud Run scales horizontally. Reconnection logic handles 300s timeout gracefully. |

---

### Files to create
- `frontend/lib/query-client.ts`
- `frontend/components/providers.tsx`
- `frontend/hooks/use-queries.ts`
- `frontend/hooks/use-audit-stream.ts`
- `frontend/hooks/use-analysis-stream.ts`
- `api/routes/ws.py`
- `api/core/ws_auth.py` — WebSocket token validation helper
- `supabase/migrations/00X_audit_change_trigger.sql`

### Files to modify (TanStack Query)
- `frontend/app/layout.tsx` — import `Providers` instead of wrapping `AuthKitProvider` directly
- `frontend/app/analyses/page.tsx`
- `frontend/app/credits/page.tsx`
- `frontend/app/credits/history/page.tsx`
- `frontend/app/credits/requests/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/audits/page.tsx`
- `frontend/app/admin/credits/page.tsx`
- `frontend/components/credits/credit-balance.tsx`
- `frontend/components/credits/purchase-credits.tsx`
- `frontend/components/analysis/analysis-selector.tsx`

### Files to modify (WebSocket real-time)
- `api/main.py` — register WebSocket router, add `asyncpg` pool startup/shutdown
- `frontend/app/audit/[id]/page.tsx` — use `useAuditStatus(id)` + `useAuditStream(id)`, remove manual polling
- `frontend/app/analysis/[id]/page.tsx` — use `useAnalysisStatus(id)` + `useAnalysisStream(id)`, remove manual polling
- `api/config.py` — add `DATABASE_URL` for `asyncpg` pool
- `api/requirements.txt` — add `asyncpg`

---

## Finding 7 — Remove Dead Supabase Client

**Decision:** Full removal (Option A path — Supabase client stays dead code).

1. **Delete** `frontend/lib/supabase.ts`
2. **Remove** `@supabase/supabase-js` from `frontend/package.json`
3. **Remove** `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from `docker-compose.yml` (lines 38-39)
4. **Remove** `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` from `docs/DEPLOYMENT.md` (Step 4 Vercel env vars + table entry)

**Files to modify:**
- `frontend/package.json`
- `docker-compose.yml`

**Files to delete:**
- `frontend/lib/supabase.ts`

**Docs to update:**
- `docs/DEPLOYMENT.md`

---

## Finding 10 — Clean Up CI/CD Stale References

### The setup
- **Backend (Gateway + SDK Worker)** → deployed to Cloud Run via `cloudbuild.yaml` (GCP Cloud Build)
- **Frontend** → deployed to Vercel (auto-deploys on push to main, CI is GitHub Actions)
- **GitHub Actions ci.yml** — runs tests, lint, typecheck, security scan, Docker build smoke tests. Does NOT deploy anything.

### What to fix in ci.yml
1. **Line 49** — Remove `orchestrator/` from `ruff check api/ workers/ orchestrator/`
   - Change to: `ruff check api/ workers/`

2. **Lines 170-175** — Remove the "Build Orchestrator image" step entirely
   - The `deploy/Dockerfile.orchestrator` does not exist

### Files to modify
- `.github/workflows/ci.yml` — remove 2 stale orchestrator references

---

## Implementation Order

1. **Finding 10** — smallest, isolated change, unblocks CI
2. **Finding 7** — small, reversible, cleanup before adding new deps
3. **Finding 5** — large change, depends on clean baseline from #7

---

## Verification

### After Finding 10
1. CI passes without orchestrator-related failures
2. `ruff check` only scans `api/ workers/`
3. No `Dockerfile.orchestrator` build step

### After Finding 7
1. `cd frontend && pnpm install` — `@supabase/supabase-js` removed
2. `pnpm build` — no broken imports
3. `docker-compose.yml` — no Supabase env vars on frontend service

### After Finding 5
1. `cd frontend && pnpm install` — `@tanstack/react-query` installed
2. `pnpm build` — compiles cleanly
3. `cd .. && pip install asyncpg` — backend dependency installed
4. Run dev server, navigate to:
   - `/dashboard` — credit balance loads, no duplicate fetches in network tab
   - `/audit/[id]` — status updates via WebSocket (not polling), instant transitions
   - `/analysis/[id]` — same WebSocket behavior
   - `/credits` — purchase flow works, success state appears
5. WebSocket connection visible in browser DevTools → Network → WS tab
6. DB trigger applied — verify with `SELECT * FROM pg_trigger WHERE tgname = 'audit_changed'`
