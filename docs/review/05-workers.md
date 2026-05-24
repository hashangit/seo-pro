# 05 — Workers

## Overview

The `workers/` directory contains a single unified worker that replaced the previous two-worker architecture (HTTP Worker + Browser Worker). It's deployed on Cloud Run with 4Gi memory, 2 CPU, and scale-to-zero.

> **Current-state review, not target architecture:** This file describes the current SDK Worker behavior. The intended direction is that every paid analysis request reaches the worker asynchronously with an `analysis_id`, a user-owned job context, and one durable result destination in `analyses`. See [../ANALYSIS_FLOW_ARCHITECTURE.md](../ANALYSIS_FLOW_ARCHITECTURE.md).

## SDK Worker (`workers/sdk_worker.py`)

The SDK Worker is a **FastAPI** service that accepts analysis requests and delegates them to the **Claude Agent SDK**, which loads skills and agents from the filesystem.

### Endpoints (14 total)

```
POST /health             — Health check (reports "degraded" if SDK unavailable)
POST /analyze             — Generic analysis (analysis_type query param)
POST /analyze/page        — Deep single-page analysis
POST /analyze/technical   — Crawlability, indexability, CWV, security
POST /analyze/content     — E-E-A-T, readability, thin content
POST /analyze/schema      — JSON-LD detection & validation
POST /analyze/visual      — Screenshots, mobile testing
POST /analyze/performance — Core Web Vitals (LCP, INP, CLS)
POST /analyze/geo         — Generative Engine Optimization
POST /analyze/sitemap     — Sitemap structure & quality
POST /analyze/hreflang    — International SEO
POST /analyze/images      — Image optimization
POST /analyze/plan        — Strategic SEO planning
POST /analyze/programmatic — Scale SEO opportunities
POST /analyze/competitor-pages — Competitor comparison pages
```

### Claude Agent SDK Integration

```python
async for message in query(
    prompt=prompt,
    options=ClaudeAgentOptions(
        cwd=project_root,                    # /app — root with skills/ and agents/
        setting_sources=["project"],         # Load from filesystem, not remote
        allowed_tools=[
            "Skill", "Task",                 # Skill invocation + subagent delegation
            "Bash",                          # Run scripts/fetch_page.py, playwright
            "Read", "Write", "Glob", "Grep", # File operations
            "WebFetch",
            "mcp__plugin_playwright_..."     # Playwright MCP tools
        ],
        permission_mode="bypassPermissions",  # Production — no human prompts
        model="claude-sonnet-4-5-20250219",
    ),
):
```

### Production vs Development

| Environment | Behavior |
|-------------|----------|
| **Production** | SDK required — returns 503 if unavailable (no fallback, users pay for quality) |
| **Development** | Falls back to `BeautifulSoup` + `httpx` direct HTML scraping if SDK unavailable |

### Result Handling

Current behavior depends on how the worker was invoked:

1. Site-audit async path: when `audit_id` is present, the worker writes the final site-audit result to `audits`.
2. Task-level path: when `task_id` is present, the worker writes task progress/result data to `audit_tasks`.
3. Individual/page sync path: the gateway proxies the worker call and writes the `analyses` record itself.
4. ~~Worker can optionally POST to orchestrator's `/task-update` endpoint~~ — callback removed (2026-05-23).

Target behavior: all paid analysis modes should be async. The worker should receive `analysis_id`, `user_id`, `analysis_mode`, `analysis_type`, quote/job metadata, and URL scope; then it should persist status and results to `analyses` through one code path.

### Key Dependencies

- `claude-agent-sdk>=0.1.0` — Agent SDK for multi-agent orchestration
- `anthropic` (transitive via SDK) — API client (configured for Z.AI endpoint)
- Playwright MCP tools — Browser automation for visual/performance analysis
- `httpx`, `beautifulsoup4` — Fallback scraping (dev only)
- `supabase` — Results persistence

## Dockerfile (`deploy/Dockerfile.sdk-worker`)

```
Base: mcr.microsoft.com/playwright/python:v1.48.0-jammy
  (Playwright + Chromium pre-installed)

Copies:
  - workers/sdk_worker.py      → /app/sdk_worker.py
  - api/utils/                  → /app/api/utils/         (URL validator)
  - api/config.py               → /app/config.py           (settings)
  - skills/                     → /app/skills/             (12 skill defs)
  - agents/                     → /app/agents/             (6 subagents)
  - scripts/                    → /app/scripts/            (fetch, parse, screenshot)

Runs: gunicorn -w 1 (single worker due to Playwright memory)
User: appuser (non-root, uid 10001)
Healthcheck: HTTP GET /health
```

## ~~Orchestrator (`orchestrator/scheduler.py`)~~ — REMOVED (2026-05-23)

The legacy orchestrator has been completely removed. It was an alternative orchestration path using Google Cloud Tasks with in-memory state (`_audit_state = {}`), but the API layer already bypassed it by dispatching directly to the SDK Worker. The orchestrator referenced `HTTP_WORKER_URL` and `BROWSER_WORKER_URL` which no longer exist.

Current site-audit orchestration flows through **API Gateway → Cloud Tasks → SDK Worker → Supabase**. Individual/page analysis still uses a synchronous **API Gateway → SDK Worker → API Gateway → Supabase** path and is targeted for migration to Cloud Tasks. The SDK Worker writes directly to Supabase for async site-audit paths and no `/task-update` callback endpoint remains.

## Scripts (`scripts/`)

Utility scripts invoked by agents via the `Bash` tool:

| Script | Purpose |
|--------|---------|
| `fetch_page.py` | HTTP fetch with headers, redirect tracking, error handling |
| `parse_html.py` | HTML parsing utilities |
| `analyze_visual.py` | Visual analysis via Playwright |
| `capture_screenshot.py` | Screenshot capture |

These are installed in the SDK Worker Docker image at `/app/scripts/`.
