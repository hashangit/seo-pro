# 04 — SEO Analysis Engine

## Overview

The SEO engine operates in two contexts:
1. **Claude Code CLI** — Instantiated by the user's Claude Code installation
2. **Cloud SDK Worker** — Instantiated by the Cloud Run worker service

Both use the same `skills/` and `agents/` files from the filesystem.

## Architecture: Hub-and-Spoke

```
                    seo/SKILL.md (Orchestrator)
                    10 slash commands
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    skills/seo-audit   skills/seo-page   skills/seo-schema  ...
    (orchestrates     (deep single-page  (schema detection)
     6 subagents)      analysis)
```

## Skills (12 total)

Each skill is a directory with a `SKILL.md` defining its purpose, tools, and workflow:

| Skill Directory | Purpose | Tools Used |
|-----------------|---------|------------|
| `seo-audit/` | Full website audit with 6 parallel subagents | Skill, Task, Bash, Read, Write |
| `seo-page/` | Deep single-page analysis | Read, Bash, Write, Grep |
| `seo-technical/` | Crawlability, indexability, security, CWV | Read, Bash, Write, Glob, Grep |
| `seo-content/` | E-E-A-T, readability, thin content detection | Read, Bash, Write, Grep |
| `seo-schema/` | JSON-LD detection, validation, generation | Read, Bash, Write |
| `seo-images/` | Image optimization (alt text, compression, lazy loading) | Read, Bash, Write |
| `seo-sitemap/` | Sitemap analysis, validation, generation | Read, Bash, Write, Glob |
| `seo-geo/` | AI Overviews (Generative Engine Optimization) | Read, Bash, Write, Grep |
| `seo-plan/` | Strategic SEO planning by business type | Read, Write |
| `seo-programmatic/` | Programmatic SEO scale analysis | Read, Bash, Write, Grep |
| `seo-competitor-pages/` | "X vs Y" / "Alternatives to X" analysis | Read, Bash, Write, Grep |
| `seo-hreflang/` | Hreflang/i18n SEO audit | Read, Bash, Write, Grep |

## Agents (6 subagents)

Each agent is a `.md` file with YAML frontmatter loaded by the Claude Agent SDK:

| Agent File | Name | Role | Tools |
|------------|------|------|-------|
| `seo-technical.md` | seo-technical | Crawlability, indexability, HTTPS, URLs, mobile, CWV, JS rendering | Read, Bash, Write, Glob, Grep |
| `seo-content.md` | seo-content | E-E-A-T signals, readability, content depth, thin content, AI citation readiness | Read, Bash, Write, Grep |
| `seo-schema.md` | seo-schema | Schema.org detection, validation, JSON-LD generation | Read, Bash, Write |
| `seo-sitemap.md` | seo-sitemap | XML sitemap validation, quality gates for location pages | Read, Bash, Write, Glob |
| `seo-performance.md` | seo-performance | Core Web Vitals (LCP, INP, CLS) measurement | Read, Bash, Write |
| `seo-visual.md` | seo-visual | Screenshots, mobile rendering, above-fold analysis | Read, Bash, Write |

## Slash Commands (10 total)

Defined in `seo/SKILL.md`:

| Command | Description |
|---------|-------------|
| `/seo audit <url>` | Full site audit — detects business type, delegates 6 subagents in parallel, returns SEO Health Score |
| `/seo page <url>` | Deep single-page analysis |
| `/seo technical <url>` | Technical SEO (8 categories) |
| `/seo content <url>` | E-E-A-T + content quality |
| `/seo schema <url>` | Schema detection/validation/generation |
| `/seo images <url>` | Image optimization |
| `/seo sitemap <url>` | Sitemap analysis or `sitemap generate` |
| `/seo geo <url>` | GEO / AI Overviews readiness |
| `/seo plan <business-type>` | Strategic planning |
| `/seo hreflang <url>` | Hreflang/i18n SEO |

## Business Type Detection

The orchestrator auto-detects from homepage signals:

| Signal | Business Type |
|--------|---------------|
| pricing, /features, /integrations, "free trial" | SaaS |
| phone, address, Google Maps embed | Local Service |
| /products, /cart, product schema | E-commerce |
| /blog, article schema, author pages | Publisher |
| /case-studies, /portfolio, client logos | Agency |

## SEO Health Score

Weighted aggregate (0-100) across 7 categories:

| Category | Weight |
|----------|--------|
| Technical SEO | 25% |
| Content Quality | 25% |
| On-Page SEO | 20% |
| Schema / Structured Data | 10% |
| Performance (CWV) | 10% |
| Images | 5% |
| AI Search Readiness | 5% |

Issues are prioritized: **Critical → High → Medium → Low**

## Reference Knowledge Base

### `seo/references/cwv-thresholds.md`

Core Web Vitals thresholds:
- **LCP** ≤ 2.5s (good), ≤ 4.0s (needs improvement), > 4.0s (poor)
- **INP** ≤ 200ms (good), ≤ 500ms (needs improvement), > 500ms (poor)
- **CLS** ≤ 0.1 (good), ≤ 0.25 (needs improvement), > 0.25 (poor)
- INP replaced FID on March 12, 2024
- LCP subparts: TTFB + load delay + load time + render delay
- Soft Navigations API for SPA measurement
- Mobile-first indexing 100% complete since July 2024

### `seo/references/eeat-framework.md`

E-E-A-T scoring framework:
- **Experience** (20%): First-hand knowledge, original photos, personal stories
- **Expertise** (25%): Credentials, technical depth, accurate sourcing
- **Authoritativeness** (25%): Industry citations, brand mentions, recognition
- **Trustworthiness** (30%): Contact info, HTTPS, editorial standards, accuracy

Key Dec 2025 update: **E-E-A-T now applies to ALL competitive queries, not just YMYL**.

### `seo/references/quality-gates.md`

Content minimums:
- Homepage: 500 words
- Service page: 800 words
- Blog post: 1,500 words
- Location pages: ⚠️ 30+ (60% unique content), 🛑 50+ (hard stop)

### `seo/references/schema-types.md`

Schema.org v29.4 reference:
- 26 active types freely recommended
- FAQPage restricted to gov/healthcare sites
- 9 deprecated types (HowTo, SpecialAnnouncement, etc.)
- Always use JSON-LD format

## Score and Recommendation Output Format

Each agent produces:
```
Score: X/100
Issues: [ordered by critical→low]
Warnings: [potential problems]
Passes: [things done well]
Recommendations: [actionable fixes with priority]
```
