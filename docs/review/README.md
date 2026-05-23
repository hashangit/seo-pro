# SEO Pro — Architecture Review

**Date:** 2026-05-23
**Version:** 2.1.0
**Branch:** main
**Commit:** a67c7b6

---

## Overview

SEO Pro is a comprehensive SEO analysis platform operating in two modes:

1. **SaaS Platform** — Full web application with credit-based pricing, WorkOS SSO authentication, and an admin dashboard
2. **Claude Code Skill** — CLI-based SEO analysis tool installed via one-command script

The platform provides 12 analysis types powered by Claude Agent SDK running on Cloud Run, with parallel subagent delegation for site audits.

---

## Review Documents

| Document | Description |
|----------|-------------|
| [01-system-architecture.md](./01-system-architecture.md) | High-level system architecture, deployment topology, data flow |
| [02-api-gateway.md](./02-api-gateway.md) | FastAPI gateway: routes, services, models, middleware, auth |
| [03-frontend.md](./03-frontend.md) | Next.js frontend: pages, components, auth flow, API integration |
| [04-seo-engine.md](./04-seo-engine.md) | SEO analysis engine: skills, agents, reference data, scoring |
| [05-workers.md](./05-workers.md) | Worker architecture: SDK worker, Cloud Tasks, Dockerfiles |
| [06-database.md](./06-database.md) | Supabase schema, RLS policies, atomic credit functions |
| [07-infrastructure.md](./07-infrastructure.md) | CI/CD, Cloud Build, deployment, Docker Compose |
| [08-supporting-modules.md](./08-supporting-modules.md) | Web search MCP, hooks, PDF ref, schema templates, scripts |
| [09-component-map.md](./09-component-map.md) | Complete component-to-component relationship map |
| [10-findings.md](./10-findings.md) | Architectural observations, gaps, and recommendations |

---

## Quick Reference

### Directory Map

```
seo-pro/
├── api/                    # FastAPI gateway (Python 3.11+)
│   ├── main.py             # Entry point
│   ├── config.py            # Centralized settings
│   ├── core/                # App factory, auth deps, middleware
│   ├── routes/              # 6 routers (health, credits, audits, analyses, admin)
│   ├── services/            # Business logic (auth, credits, audits, email, Cloud Tasks)
│   ├── models/              # Pydantic v2 models
│   ├── scanner/             # SiteScanner (sitemap/crawl URL discovery)
│   ├── utils/               # SSRF prevention, URL validation
│   └── tests/               # Pytest test suite
│
├── frontend/               # Next.js 15 app (TypeScript, Tailwind, shadcn/ui)
│   ├── app/                 # App Router pages (dashboard, audits, analyses, credits, admin)
│   ├── components/          # AnalysisSelector, AuditForm, AuthButton, CreditBalance, ui/
│   ├── hooks/               # useAuth hook
│   ├── lib/                 # API client, auth, supabase, utils, logger
│   └── middleware.ts        # WorkOS AuthKit middleware
│
├── workers/                # Worker services
│   └── sdk_worker.py        # Unified SDK worker (Claude Agent SDK)
│
├── ~~orchestrator/~~        # REMOVED 2026-05-23 — legacy Cloud Tasks orchestrator
│
├── agents/                 # 6 subagent definitions (Markdown + frontmatter)
│   ├── seo-technical.md
│   ├── seo-content.md
│   ├── seo-schema.md
│   ├── seo-sitemap.md
│   ├── seo-performance.md
│   └── seo-visual.md
│
├── skills/                 # 12 specialized skills (each with SKILL.md)
│   ├── seo-audit/           # Full site audit orchestrator
│   ├── seo-page/
│   ├── seo-technical/
│   ├── seo-content/
│   ├── seo-schema/
│   ├── seo-geo/
│   ├── seo-sitemap/
│   ├── seo-hreflang/
│   ├── seo-images/
│   ├── seo-plan/
│   ├── seo-programmatic/
│   └── seo-competitor-pages/
│
├── seo/                    # Main orchestrator SKILL.md + reference data
│   ├── SKILL.md             # Top-level skill (10 commands)
│   └── references/          # CWV thresholds, E-E-A-T framework, quality gates, schema types
│
├── supabase/               # Database schema & migrations
│   └── migrations/001_initial_schema.sql  # Complete schema + RLS + functions
│
├── deploy/                 # Dockerfiles
│   ├── Dockerfile.gateway
│   └── Dockerfile.sdk-worker
│   # ~~Dockerfile.orchestrator~~ — REMOVED 2026-05-23
│
├── web-search/             # MCP server for Google search (TypeScript)
├── hooks/                  # Claude Code hooks (pre-commit SEO checks, schema validation)
├── pdf/                    # Google SEO reference document
├── schema/                 # JSON-LD templates (VideoObject, ProductGroup, etc.)
├── scripts/                # Browser automation utilities (fetch, parse, screenshot)
│
└── docs/                   # Documentation
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    ├── DEVELOPER_GUIDE.md
    └── review/              # THIS REVIEW
```

### Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Radix UI |
| Backend API | FastAPI, Python 3.11+, Pydantic v2 |
| AI Engine | Claude Agent SDK via Z.AI (GLM-4.7 via Anthropic-compatible API) |
| Auth | WorkOS AuthKit (SSO: Google, GitHub) |
| Database | Supabase PostgreSQL 17 with RLS |
| Browser | Playwright (via MCP tools) |
| Deployment | Google Cloud Run, Cloud Tasks, Artifact Registry |
| CI/CD | GitHub Actions, Cloud Build |
| Local Dev | Docker Compose (gateway + frontend) |

### Key Relationships

```
User/Browser → Next.js Frontend (Vercel)
                   │
                   ▼
            FastAPI Gateway (Cloud Run)
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Supabase    SDK Worker  Cloud Tasks
   (Postgres)  (Cloud Run)  (Queue)
                   │
                   ▼
            Claude Agent SDK
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     Skills/    Agents/    Scripts/
    (12 skill  (6 sub-    (fetch_page,
     defs)     agents)    screenshot, etc.)
```
