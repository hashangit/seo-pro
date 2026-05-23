# 09 — Complete Component Relationship Map

## File-Level Dependencies

```
Frontend (TypeScript)
═══════════════════════
frontend/middleware.ts
  └─ @workos-inc/authkit-nextjs

frontend/lib/auth/index.ts
  └─ @workos-inc/authkit-nextjs

frontend/lib/api-client.ts (server-side)
  ├─ frontend/lib/auth (withAuth)
  └─ NEXT_PUBLIC_API_URL → Gateway

frontend/lib/api.ts (client-side)
  └─ NEXT_PUBLIC_API_URL → Gateway

frontend/hooks/use-auth.ts
  └─ @workos-inc/authkit-nextjs (useAuth, useAccessToken)

frontend/app/**/page.tsx (Server Components)
  ├─ frontend/lib/api-client.ts → Gateway
  ├─ frontend/components/*
  └─ frontend/lib/utils.ts

frontend/app/**/page.tsx (Client Components)
  ├─ frontend/hooks/use-auth.ts → WorkOS
  ├─ frontend/lib/api.ts → Gateway
  └─ frontend/components/*

frontend/components/analysis/AnalysisSelector.tsx
  ├─ frontend/lib/api.ts → Gateway
  ├─ frontend/hooks/use-auth.ts → WorkOS
  └─ frontend/components/ui/*

═══ Gateway (Python) ═══
api/main.py
  ├─ api/core/app.py (create_app)
  ├─ api/config.py (get_settings)
  ├─ api/routes/health.py
  ├─ api/routes/credits.py
  ├─ api/routes/credit_requests.py
  ├─ api/routes/admin/credits.py
  ├─ api/routes/audits.py
  └─ api/routes/analyses.py

api/core/app.py
  ├─ api/core/middleware.py
  ├─ api/rate_limiter.py
  └─ fastapi (CORSMiddleware)

api/core/dependencies.py
  ├─ api/services/auth.py (verify_token, sync_user)
  └─ api/config.py

api/routes/health.py
  ├─ api/core/dependencies.py (get_internal_secret)
  ├─ api/services/supabase.py
  ├─ api/services/auth.py
  └─ api/config.py

api/routes/credits.py
  ├─ api/core/dependencies.py (get_current_user)
  ├─ api/services/supabase.py
  └─ api/config.py

api/routes/credit_requests.py
  ├─ api/core/dependencies.py (get_current_user)
  ├─ api/services/credit_requests.py
  └─ api/models/credit_requests.py

api/routes/admin/credits.py
  ├─ api/core/dependencies.py (get_current_user)
  ├─ api/services/credit_requests.py
  └─ api/services/email.py

api/routes/audits.py
  ├─ api/core/dependencies.py (get_current_user)
  ├─ api/services/audits.py
  ├─ api/services/credits.py
  ├─ api/scanner/site.py (SiteScanner)
  ├─ api/utils/url_validator.py
  └─ api/models/audits.py

api/routes/analyses.py
  ├─ api/core/dependencies.py (get_current_user)
  ├─ api/services/analyses.py
  ├─ api/services/credits.py
  ├─ api/services/cloud_tasks.py
  └─ api/models/analyses.py

api/services/analyses.py
  ├─ api/services/credits.py
  ├─ api/services/supabase.py
  ├─ api/config.py (SDK_WORKER_URL)
  └─ api/utils/url_validator.py

api/services/audits.py
  ├─ api/services/credits.py (deduct, refund, calculate)
  ├─ api/services/cloud_tasks.py
  ├─ api/services/supabase.py
  └─ api/utils/url_validator.py

api/services/cloud_tasks.py
  ├─ google-cloud-tasks
  └─ api/config.py

api/services/auth.py
  ├─ api/services/supabase.py
  ├─ api/config.py (WorkOS settings)
  └─ PyJWT

api/services/credit_requests.py
  ├─ api/services/supabase.py
  ├─ api/services/email.py
  └─ api/config.py

api/services/email.py
  └─ sendgrid

api/services/credits.py
  ├─ api/services/supabase.py
  └─ api/config.py

api/services/supabase.py
  └─ supabase-py

═══ SDK Worker (Python) ═══
workers/sdk_worker.py
  ├─ api/config.py
  ├─ api/utils/url_validator.py
  ├─ claude_agent_sdk (query, ClaudeAgentOptions)
  ├─ supabase (update_task_status)
  └─ httpx, beautifulsoup4 (fallback, dev only)

═══ Orchestrator (Python, legacy) ═══
orchestrator/scheduler.py
  ├─ api/utils/url_validator.py
  ├─ google-cloud-tasks
  └─ supabase

═══ SEO Engine (Markdown-based) ═══
seo/SKILL.md
  ├─ skills/seo-audit/SKILL.md
  ├─ skills/seo-page/SKILL.md
  ├─ skills/seo-technical/SKILL.md
  ├─ skills/seo-content/SKILL.md
  ├─ skills/seo-schema/SKILL.md
  ├─ skills/seo-images/SKILL.md
  ├─ skills/seo-sitemap/SKILL.md
  ├─ skills/seo-geo/SKILL.md
  ├─ skills/seo-plan/SKILL.md
  ├─ skills/seo-programmatic/SKILL.md
  ├─ skills/seo-competitor-pages/SKILL.md
  └─ skills/seo-hreflang/SKILL.md

skills/seo-audit/SKILL.md
  ├─ agents/seo-technical.md
  ├─ agents/seo-content.md
  ├─ agents/seo-schema.md
  ├─ agents/seo-sitemap.md
  ├─ agents/seo-performance.md
  └─ agents/seo-visual.md

agents/seo-technical.md → scripts/fetch_page.py, scripts/parse_html.py
agents/seo-content.md → scripts/fetch_page.py, seo/references/eeat-framework.md
agents/seo-schema.md → seo/references/schema-types.md
agents/seo-performance.md → seo/references/cwv-thresholds.md
agents/seo-sitemap.md → seo/references/quality-gates.md
agents/seo-visual.md → scripts/capture_screenshot.py, scripts/analyze_visual.py

═══ Database ═══
supabase/migrations/001_initial_schema.sql
  ├─ 7 tables + RLS + indexes + triggers
  └─ 6 functions (deduct, add, refund credits, create/update analysis, cleanup)

═══ CLI Install ═══
install.sh / install.ps1
  └─ Copies skills/ + agents/ + hooks/ + scripts/ + seo/ → ~/.claude/skills/seo/

═══ Web Search MCP ═══
web-search/src/index.ts
  ├─ web-search/src/search.ts
  ├─ web-search/src/browser.ts
  ├─ web-search/src/utils.ts
  └─ @modelcontextprotocol/sdk

═══ Deploy ═══
deploy/Dockerfile.gateway → api/ + orchestrator/
deploy/Dockerfile.sdk-worker → workers/sdk_worker.py + api/utils/ + api/config.py + skills/ + agents/ + scripts/
deploy/Dockerfile.orchestrator → orchestrator/scheduler.py
```

## Service Communication Map

```
Frontend ──HTTP──▶ Gateway ──HTTP──▶ SDK Worker
    │                  │                  │
    │                  │                  │
    ▼                  ▼                  ▼
 WorkOS           Supabase DB        Supabase DB
 (Auth)           (Data)             (Results)

Gateway ──Cloud Tasks──▶ ████████████ ──HTTP──▶ SDK Worker
                            Queue

Gateway ──SMTP──▶ SendGrid (Emails)

SDK Worker ──HTTP (Anthropic API)──▶ Z.AI (GLM-4.7)

CLI (Claude Code) ──Filesystem──▶ skills/ + agents/
CLI (Claude Code) ──stdio MCP──▶ web-search/

Orchestrator (legacy) ──Cloud Tasks──▶ Queue ──▶ Worker URLs
```

## Technology Stack Interactions

```
┌─────────────────────────────────────────────────────────┐
│  TypeScript/React        Python/FastAPI                 │
│  ┌─────────────┐        ┌──────────────────────┐       │
│  │ Next.js 15  │──REST──▶│ Gateway (Cloud Run)  │       │
│  │ (Vercel)    │  JSON  │ │ - Auth (WorkOS)      │       │
│  └─────────────┘        │ │ - Credits            │       │
│         │               │ │ - Audit orchestration│       │
│         ▼               │ └──────────┬───────────┘       │
│  ┌─────────────┐        │            │                   │
│  │ WorkOS      │        │            ▼                   │
│  │ AuthKit     │        │ ┌──────────────────────┐       │
│  │ (SSO/OAuth) │        │ │ SDK Worker           │       │
│  └─────────────┘        │ │ (Cloud Run, 4Gi)     │       │
│                         │ │ - Claude Agent SDK   │       │
│  ┌─────────────┐        │ │ - Playwright MCP     │       │
│  │ Tailwind    │        │ └──────────┬───────────┘       │
│  │ shadcn/ui   │        │            │                   │
│  │ Radix UI    │        │            ▼                   │
│  └─────────────┘        │ ┌──────────────────────┐       │
│                         │ │ Z.AI API             │       │
│  ┌─────────────┐        │ │ (Anthropic-compat)   │       │
│  │ Supabase JS │        │ │ GLM-4.7 model        │       │
│  │ (types)     │        │ └──────────────────────┘       │
│  └─────────────┘        │                                │
└─────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
    ┌─────────────────┐    ┌─────────────────┐
    │ Supabase        │    │ Google Cloud    │
    │ PostgreSQL 17   │    │ - Cloud Tasks   │
    │ (Managed)       │    │ - Secret Mgr    │
    └─────────────────┘    │ - Cloud Run     │
                           └─────────────────┘

    ┌─────────────────┐
    │ SendGrid        │
    │ Transactional   │
    │ Email           │
    └─────────────────┘
```

## 12 Analysis Types → Skills → Agents Map

| Analysis Type | Skill (CLI command) | Agent (subagent) | Worker Endpoint |
|---------------|---------------------|------------------|-----------------|
| Technical SEO | `/seo technical` | seo-technical | `/analyze/technical` |
| On-Page SEO | (part of `/seo page`) | (n/a) | (in page analysis) |
| Content Quality | `/seo content` | seo-content | `/analyze/content` |
| Schema Markup | `/seo schema` | seo-schema | `/analyze/schema` |
| Image Optimization | `/seo images` | (n/a) | `/analyze/images` |
| Internal Linking | (part of `/seo page`) | (n/a) | (in page analysis) |
| Sitemap Analysis | `/seo sitemap` | seo-sitemap | `/analyze/sitemap` |
| AI Search (GEO) | `/seo geo` | (n/a) | `/analyze/geo` |
| Competitor Analysis | `/seo competitor-pages` | (n/a) | `/analyze/competitor-pages` |
| Hreflang/i18n | `/seo hreflang` | (n/a) | `/analyze/hreflang` |
| Programmatic SEO | `/seo programmatic` | (n/a) | `/analyze/programmatic` |
| Page Speed | (part of audit) | seo-performance | `/analyze/performance` |
| Full Page Audit | `/seo page` | (all 6) | `/analyze/page` |
| Full Site Audit | `/seo audit` | (all 6) | `/analyze` |
| Strategic Planning | `/seo plan` | (n/a) | `/analyze/plan` |
