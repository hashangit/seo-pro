# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-26

### Added - SaaS Platform (MAJOR)

This release transforms SEO Pro from a CLI-only tool into a full SaaS platform while maintaining 100% backward compatibility with the Claude Code Skill mode.

#### Web Application
- **Next.js Frontend**: TypeScript + Tailwind CSS + shadcn/ui components
- **FastAPI Gateway**: RESTful API with authentication, credits, and orchestration
- **WorkOS AuthKit**: Enterprise-grade authentication with SSO support (Google, GitHub, etc.)
- **Supabase PostgreSQL**: Multi-tenant database with Row-Level Security (RLS)
- **Docker Compose**: One-command local development environment

#### Credit System
- **Credit-Based Pricing**: $1 = 8 credits with tiered analysis costs
- **Real-Time Balance Tracking**: Live credit balance updates
- **Atomic Operations**: Race-condition-safe credit deduction with PostgreSQL transactions
- **Transaction History**: Complete audit trail of all credit activity
- **Never-Expiring Credits**: Purchase once, use anytime
- **Dev Mode**: Unlimited access for development/testing

#### Analysis Pricing
| Mode | Credits | Description |
|------|---------|-------------|
| Quick Analysis | 1 per report | Individual analysis types |
| Full Page Audit | 8 per page | All 12 types on one page (33% discount) |
| Full Site Audit | 7 per page | All 12 types across entire site |

#### Cloud Deployment
- **Google Cloud Run**: Scale-to-zero serverless deployment
- **Cloud Tasks**: Async job processing with `sdk-worker-queue`
- **Secret Manager**: Secure API key storage
- **CI/CD Pipeline**: GitHub Actions workflow for automated deployments

### Changed - Worker Architecture (BREAKING)

#### Unified SDK Worker
- **Migration**: Replaced `browser_worker` and `http_worker` with unified `sdk_worker`
- **Claude Agent SDK**: Filesystem-based Skills and Agents for multi-agent orchestration
- **GLM-4.7 Integration**: Z.AI API for cost-effective AI analysis via Anthropic-compatible endpoint
- **Playwright CLI**: Browser automation via concise Bash commands (vs MCP tool schemas)

#### API Restructure
- **Modular Architecture**: `api/core/`, `api/models/`, `api/services/`, `api/routes/`
- **Dedicated Route Modules**: `analyses.py`, `audits.py`, `credits.py`, `health.py`
- **Centralized Dependencies**: `api/core/dependencies.py` for shared services
- **Comprehensive Models**: Pydantic models for all request/response types

### Added - Frontend Components

#### Pages
- `/analyses` - Analysis history with filtering by type/status
- `/analysis/[id]` - Detailed analysis results with scores and recommendations
- `/audits` - Full site audit management
- `/audit/[id]` - Audit progress and results
- `/credits` - Credit balance and purchase flow
- `/credits/history` - Transaction history
- `/pricing` - Pricing tiers and feature comparison
- `/features` - Feature showcase with 12 analysis types

#### Components
- **Analysis Selector**: Interactive tool to choose analysis types with live cost preview
- **Audit Form**: URL input with site discovery and cost estimation
- **Auth Button**: WorkOS login/logout with user profile display
- **Credit Balance**: Real-time balance widget
- **Error Boundary**: Graceful error handling with retry

### Added - Security Features

- **SSRF Prevention**: URL validation with private IP blocking
- **Row-Level Security**: Data isolation per user/organization in Supabase
- **JWT Authentication**: WorkOS token validation with audience verification
- **CORS Configuration**: Origin whitelisting for API access
- **Input Sanitization**: Injection prevention across all endpoints

### Added - API Endpoints

#### System
- `GET /api/v1/health` - Service health check
- `GET /api/v1/health/ready` - Dependency readiness check

#### Credits
- `GET /api/v1/credits/balance` - Current credit balance
- `GET /api/v1/credits/history` - Transaction history with pagination

#### Audits
- `POST /api/v1/audit/discover` - Discover site URLs from sitemap/crawling
- `POST /api/v1/audit/estimate` - Get cost estimate before running
- `POST /api/v1/audit/run` - Execute full site audit
- `GET /api/v1/audit/{id}` - Audit status and results
- `GET /api/v1/audit` - List user's audits with filtering

#### Analysis
- `POST /api/v1/analyze/estimate` - Estimate credits for any analysis
- `GET /api/v1/analyses` - List analyses with filtering
- `GET /api/v1/analyses/{id}` - Single analysis details
- `POST /api/v1/analyze/{type}` - Run individual analysis (12 types)
- `POST /api/v1/analyze/page` - Full page audit (all 12 types)

### Added - Database Schema

- `users` - User profiles and credit balances
- `organizations` - Multi-tenant structure
- `credit_transactions` - Complete audit trail
- `analyses` - Individual analysis tracking with status
- `audits` - Full site audit management
- `audit_tasks` - Subagent progress tracking
- `pending_audits` - Quote management for large audits
- `cached_pages` - 24-hour TTL cache for performance

### Added - Infrastructure

- **Dockerfiles**: `Dockerfile.gateway`, `Dockerfile.sdk-worker`
- **Docker Compose**: Full stack orchestration for local development
- **Cloud Build**: `cloudbuild.yaml` for automated deployments
- **Environment Config**: Centralized `config.py` with validation
- **Rate Limiting Documentation**: `docs/RATE-LIMITING.md`

### Added - Developer Experience

- **Local Development Guide**: `docs/LOCAL_DEVELOPMENT.md`
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Architecture Documentation**: Updated `docs/ARCHITECTURE.md`
- **Features Overview**: `docs/FEATURES.md` with pricing and capabilities
- **.env.example**: Template for all required environment variables

### Changed

- **Frontend Auth**: Migrated from `route.tsx` to `page.tsx` callback pattern
- **Auth Module**: Converted `lib/auth.ts` to `lib/auth.tsx` for React components
- **Documentation**: Reorganized docs into `docs/` folder
- **Rate Limiting**: Enhanced with configurable tiers and per-endpoint limits

### Removed

- `browser_worker.py` - Replaced by unified SDK worker
- `http_worker.py` - Replaced by unified SDK worker
- Legacy worker-specific Dockerfiles

---

## [1.1.0] - 2026-02-07

### Security (CRITICAL)
- **urllib3 ≥2.6.3**: Fixes CVE-2026-21441 (CVSS 8.9) - decompression bypass vulnerability
- **lxml ≥6.0.2**: Updated from 5.3.2 for additional libxml2 security patches
- **Pillow ≥12.1.0**: Fixes CVE-2025-48379
- **playwright ≥1.55.1**: Fixes CVE-2025-59288 (macOS)
- **requests ≥2.32.4**: Fixes CVE-2024-47081, CVE-2024-35195

### Added
- **GEO (Generative Engine Optimization) major enhancement**:
  - Brand mention analysis (3× more important than backlinks for AI visibility)
  - AI crawler detection (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, etc.)
  - llms.txt standard detection and recommendations
  - RSL 1.0 (Really Simple Licensing) detection
  - Passage-level citability scoring (optimal 134-167 words)
  - Platform-specific optimization (Google AI Overviews vs ChatGPT vs Perplexity)
  - Server-side rendering checks for AI crawler accessibility
- **LCP Subparts analysis**: TTFB, resource load delay, resource load time, render delay
- **Soft Navigations API detection** for SPA CWV measurement limitations
- **Schema.org v29.4 additions**: ConferenceEvent, PerformingArtsEvent, LoyaltyProgram
- **E-commerce schema updates**: returnPolicyCountry now required, organization-level policies

### Changed
- **E-E-A-T framework**: Updated for December 2025 core update - now applies to ALL competitive queries, not just YMYL
- **SKILL.md description**: Expanded to leverage new 1024-character limit
- **Schema deprecations expanded**: Added ClaimReview, VehicleListing (June 2025)
- **WebApplication schema**: Added as correct type for browser-based SaaS (vs SoftwareApplication)

### Fixed
- Schema-types.md now correctly distinguishes SoftwareApplication (apps) vs WebApplication (SaaS)

---

## [1.0.0] - 2026-02-07

### Added
- Initial release of SEO Pro
- 9 specialized skills: audit, page, sitemap, schema, images, technical, content, geo, plan
- 6 subagents for parallel analysis: seo-technical, seo-content, seo-schema, seo-sitemap, seo-performance, seo-visual
- Industry templates: SaaS, local service, e-commerce, publisher, agency, generic
- Schema library with deprecation tracking:
  - HowTo schema marked deprecated (September 2023)
  - FAQ schema restricted to government/healthcare sites only (August 2023)
  - SpecialAnnouncement schema marked deprecated (July 31, 2025)
- AI Overviews / GEO optimization skill (seo-geo) - new for 2026
- Core Web Vitals analysis using current metrics:
  - LCP (Largest Contentful Paint): <2.5s
  - INP (Interaction to Next Paint): <200ms - replaced FID on March 12, 2024
  - CLS (Cumulative Layout Shift): <0.1
- E-E-A-T framework updated to September 2025 Quality Rater Guidelines
- Quality gates for thin content and doorway page prevention:
  - Warning at 30+ location pages
  - Hard stop at 50+ location pages
- Pre-commit and post-edit automation hooks
- One-command install and uninstall scripts (Unix and Windows)
- Bounded Python dependency pinning with CVE-aware minimums (lxml >= 5.3.2)

### Architecture
- Follows Anthropic's official Claude Code skill specification (February 2026)
- Standard directory layout: `scripts/`, `references/`, `assets/`
- Valid hook matchers (tool name only, no argument patterns)
- Correct subagent frontmatter fields (name, description, tools)
- CLI command is `claude` (not `claude-code`)
