# 05 — Workers

## Overview

The `workers/` directory contains a single unified worker that replaced the previous two-worker architecture (HTTP Worker + Browser Worker). It's deployed on Cloud Run with 4Gi memory, 2 CPU, and scale-to-zero.

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

On completion:
1. Worker writes results directly to `audit_tasks` table in Supabase (via `update_task_status()`)
2. Worker can optionally POST to orchestrator's `/task-update` endpoint

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

## Orchestrator (`orchestrator/scheduler.py`)

The legacy orchestrator is bundled into the Gateway Docker image but represents an alternative orchestration path using Google Cloud Tasks.

### Key Characteristics

- **In-memory state**: Uses a Python dict `_audit_state` for tracking in-flight audits
- **6 hardcoded tasks**: technical, content, schema, sitemap, programmatic, visual
- **References old worker URLs**: HTTP_WORKER_URL, BROWSER_WORKER_URL (predates unified SDK worker)
- **Cloud Tasks integration**: Uses `google-cloud-tasks` library v2 API
- **Idempotency**: Supports `idempotency_key` to prevent duplicate audit submissions

### Orchestration Flow (Orchestrator Path)

```
1. POST /submit → submit_audit()
   - SSRF validation
   - Idempotency check
   - Create audits record (status=queued)

2. submit_audit_job() creates 6 Cloud Tasks
   - Each task → POST to worker URL
   - 3 retries with exponential backoff
   - 5s scheduling delay

3. Cloud Tasks delivers to worker endpoints
   - Worker processes analysis
   - Worker calls POST /task-update on orchestrator

4. POST /task-update → update_audit_state_on_task_completion()
   - Increments completed_tasks in _audit_state
   - When all complete → update audits status=completed

5. Optional direct DB path:
   - Workers can update audit_tasks directly in Supabase
   - Orchestrator also receives task-update callbacks
```

### Architectural Note

The orchestrator references `HTTP_WORKER_URL` and `BROWSER_WORKER_URL` but the deployment config (`cloudbuild-gateway.yaml`) only sets `SDK_WORKER_URL`. The API layer (`api/services/cloud_tasks.py`) bypasses the orchestrator and submits tasks directly to the SDK Worker. This suggests the orchestrator is in a transitional/legacy state.

## Scripts (`scripts/`)

Utility scripts invoked by agents via the `Bash` tool:

| Script | Purpose |
|--------|---------|
| `fetch_page.py` | HTTP fetch with headers, redirect tracking, error handling |
| `parse_html.py` | HTML parsing utilities |
| `analyze_visual.py` | Visual analysis via Playwright |
| `capture_screenshot.py` | Screenshot capture |

These are installed in the SDK Worker Docker image at `/app/scripts/`.
