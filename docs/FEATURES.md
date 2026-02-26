# SEO Pro Features

SEO Pro operates in two modes:
- **Claude Code Skill**: CLI-based SEO analysis tool (`/seo` commands)
- **SaaS Platform**: Web application with credit-based pricing

---

## SaaS Platform Features

### Authentication & User Management
- **WorkOS AuthKit Integration**: Enterprise-grade authentication
- **Organization Support**: Multi-tenant with organization-level access
- **JWT-Based Sessions**: Secure token-based authentication
- **Lazy User Sync**: Automatic user creation on first login

### Credit System
- **Credit-Based Pricing**: $1 = 8 credits
- **Real-Time Balance Tracking**: Live credit balance updates
- **Transaction History**: Complete audit trail of all credit activity
- **Atomic Credit Operations**: Race-condition-safe credit deduction
- **Never-Expiring Credits**: Purchase once, use anytime
- **Dev Mode**: Unlimited access for development/testing

### Analysis Modes

| Mode | Credits | Description |
|------|---------|-------------|
| Quick Analysis | 1 per report | Individual analysis types |
| Full Page Audit | 8 per page | All 12 types on one page (33% discount) |
| Full Site Audit | 7 per page | All 12 types across entire site |

### User Interface
- **Modern Next.js Frontend**: TypeScript with Tailwind CSS
- **Responsive Design**: Desktop and mobile optimized
- **Analysis Selector**: Interactive tool to choose analysis types
- **Real-Time Progress**: Live status updates during analysis
- **Analysis History**: Filterable list of past analyses
- **Detailed Results View**: Comprehensive breakdown with scores, issues, and recommendations
- **Credit Purchase Flow**: Streamlined top-up experience

---

## Analysis Types (12 Total)

### 1. Technical SEO (`/api/v1/analyze/technical`)
Deep inspection of the technical foundation.

- **Crawlability & Indexability**: robots.txt, sitemaps, canonicals, noindex tags, redirect chains
- **Core Web Vitals**: LCP, INP (replaces FID), CLS
- **Security**: HTTPS validation and security header analysis
- **URL Structure**: Clean URLs, depth analysis, path optimization
- **Mobile Optimization**: Viewport settings, touch targets, mobile-first readiness
- **JavaScript Rendering**: CSR vs SSR detection

### 2. Content Quality & E-E-A-T (`/api/v1/analyze/content`)
Evaluates content based on Google's Quality Rater Guidelines.

- **E-E-A-T Scoring**: Experience, Expertise, Authoritativeness, Trustworthiness
- **AI Citation Readiness**: Scores content for AI search engine citations
- **Readability Analysis**: Word count thresholds per page type, readability metrics
- **Content Freshness**: Update signals and "fake freshness" detection
- **AI Content Assessment**: Flags low-quality AI-generated content markers
- **Topical Authority**: Domain expertise evaluation

### 3. Schema & Structured Data (`/api/v1/analyze/schema`)
Maximizes rich result opportunities and entity clarity.

- **Multi-Format Detection**: JSON-LD, Microdata, RDFa
- **Validation**: Against Google's latest requirements and deprecation notices
- **Deprecated Type Awareness**: FAQ/HowTo changes and other deprecations
- **Opportunity Detection**: Suggests missing schema types based on content
- **Code Generation**: Ready-to-use JSON-LD snippets
- **Rich Snippets Optimization**: Enhanced search appearance

### 4. AI Search & GEO Optimization (`/api/v1/analyze/geo`)
Generative Engine Optimization for AI-first search.

- **Citability Scoring**: Optimizes "answer blocks" (134-167 words) for AI citations
- **Structural Readability**: Headings, lists, tables for AI parsing
- **AI Crawler Management**: GPTBot, ClaudeBot, PerplexityBot configuration
- **llms.txt Support**: Validates and recommends `/llms.txt` implementation
- **Brand Mention Analysis**: YouTube, Reddit, Wikipedia presence
- **AI Overview Optimization**: SGE/AI Overview readiness

### 5. Sitemap Architecture (`/api/v1/analyze/sitemap`)
Validates and optimizes sitemap structure.

- **XML Validation**: Format, URL count, status code verification
- **lastmod Accuracy**: Verifies freshness against actual page updates
- **Coverage Analysis**: Sitemap vs crawled pages comparison
- **Quality Gates**: Hard stops and warnings for excessive locations
- **Industry Templates**: Interactive generation with domain-specific templates
- **Templated Page Detection**: Identifies potential quality issues

### 6. International SEO (`/api/v1/analyze/hreflang`)
Global reach validation and generation.

- **Reciprocity Validation**: A→B, B→A return tag consistency
- **ISO Code Verification**: Language (ISO 639-1) and region (ISO 3166-1) codes
- **Sitemap Integration**: Generates hreflang XML sitemap snippets
- **Protocol & Canonical Checks**: Alignment between hreflang and canonical URLs
- **Cross-Language Link Analysis**: Identifies broken or missing connections
- **x-default Validation**: Proper implementation checking

### 7. Image Optimization (`/api/v1/analyze/images`)
Ensures optimized image delivery and accessibility.

- **Oversized Image Detection**: Performance-impacting images
- **Missing Alt Text**: Accessibility and SEO issues
- **Modern Format Recommendations**: WebP/AVIF suggestions
- **Responsive srcset Validation**: Mobile optimization
- **CLS Prevention**: Missing dimension attributes
- **Lazy Loading Analysis**: Performance optimization opportunities

### 8. Visual Analysis (`/api/v1/analyze/visual`)
*Requires Playwright*

- **Multi-Viewport Screenshots**: Desktop and mobile captures
- **Above-the-Fold Analysis**: CTA and H1 visibility without scrolling
- **Mobile Rendering Issues**: Responsive design problems
- **Visual Hierarchy Assessment**: Design effectiveness
- **Element Visibility Scoring**: Key content placement

### 9. Performance & Core Web Vitals (`/api/v1/analyze/performance`)
*Requires Playwright*

- **LCP Measurement**: Largest Contentful Paint timing
- **INP Analysis**: Interaction to Next Paint (replaces FID)
- **CLS Scoring**: Cumulative Layout Shift impact
- **Resource Optimization**: Script and stylesheet recommendations
- **Third-Party Script Impact**: Performance bottlenecks
- **Caching Header Analysis**: Browser caching opportunities

### 10. Strategic SEO Planning (`/api/v1/analyze/plan`)
Creates industry-specific SEO strategies.

- **5 Industry Templates**: SaaS, E-commerce, Local Service, Publisher, Agency
- **Competitive Analysis Framework**: Market positioning insights
- **Content Strategy Roadmap**: Topic clusters and content gaps
- **Implementation Timeline**: Phased approach recommendations
- **Keyword Clustering**: Opportunity identification
- **KPI Frameworks**: Measurable success metrics

### 11. Programmatic SEO (`/api/v1/analyze/programmatic`)
Safeguards for building SEO pages at scale.

- **Template Page Pattern Analysis**: Identifies scaling opportunities
- **Data Source Quality Evaluation**: Uniqueness and value assessment
- **Thin Content Safeguards**: "Doorway page" penalty prevention
- **Index Bloat Prevention**: Pagination and faceted navigation strategies
- **Internal Linking Automation**: Hub/spoke and breadcrumb planning
- **Canonical Strategy**: Scale-appropriate URL handling

### 12. Competitor Comparison Pages (`/api/v1/analyze/competitor-pages`)
Optimizes "X vs Y" and "Alternatives to X" pages.

- **SEO Optimization**: Title, meta, headings, schema markup
- **GEO Optimization**: AI search engine visibility
- **AEO Optimization**: Voice/answer engine readiness
- **Feature Matrix Schema**: AggregateRating and Offer markup
- **Fairness Guidelines**: Accurate competitor representation
- **Source Citation Validation**: Claim verification

---

## Full Website Audit

Comprehensive parallel analysis across entire websites (up to 500 pages).

### Features
- **Parallel Subagents**: 6 specialized agents (Technical, Content, Schema, Sitemap, Performance, Visual)
- **Business Type Detection**: Auto-detects SaaS, Ecommerce, Local, Publisher, Agency
- **SEO Health Score**: Overall score (0-100) based on weighted categories
- **Prioritized Action Plan**: Tasks ranked Critical → Low
- **Comprehensive Reporting**: Detailed `FULL-AUDIT-REPORT.md` and `ACTION-PLAN.md`

### URL Discovery
- **Sitemap Parsing**: Automatic discovery from robots.txt
- **Manual Sitemap Support**: Custom sitemap URL input
- **Homepage Crawling**: Fallback link extraction
- **Confidence Scoring**: Discovery method reliability rating

---

## API Endpoints

### System
- `GET /api/v1/health` - Service health check
- `GET /api/v1/health/ready` - Dependency readiness check

### Credits
- `GET /api/v1/credits/balance` - Current credit balance
- `GET /api/v1/credits/history` - Transaction history

### Audits
- `POST /api/v1/audit/discover` - Discover site URLs
- `POST /api/v1/audit/estimate` - Get cost estimate
- `POST /api/v1/audit/run` - Execute audit
- `GET /api/v1/audit/{id}` - Audit status and results
- `GET /api/v1/audit` - List user's audits

### Analysis
- `POST /api/v1/analyze/estimate` - Estimate credits for any analysis
- `GET /api/v1/analyses` - List analyses with filtering
- `GET /api/v1/analyses/{id}` - Single analysis details
- `POST /api/v1/analyze/{type}` - Run individual analysis (12 types)
- `POST /api/v1/analyze/page` - Full page audit (8 credits)

---

## Architecture

### Backend
- **FastAPI Gateway**: Request routing, auth, orchestration
- **Cloud Run Deployment**: Scale-to-zero (min_instances=0)
- **Cloud Tasks**: Async job processing
- **Supabase**: PostgreSQL database with RLS

### Worker
- **Unified SDK Worker**: Claude Agent SDK-based analysis engine
- **Filesystem Skills/Agents**: Modular capability system
- **Playwright MCP**: Browser automation for visual analysis
- **Scale-to-Zero**: Cost-efficient processing

### Database Schema
- `users` - User profiles and credit balances
- `organizations` - Multi-tenant structure
- `credit_transactions` - Complete audit trail
- `analyses` - Individual analysis tracking
- `audits` - Full site audit management
- `audit_tasks` - Subagent progress tracking
- `pending_audits` - Quote management
- `cached_pages` - 24-hour TTL cache

---

## Security Features

- **URL Validation**: SSRF prevention
- **Row-Level Security**: Data isolation per user/org
- **WorkOS JWT Authentication**: Enterprise-grade auth
- **Service Role Separation**: Privilege boundaries
- **Input Sanitization**: Injection prevention
- **CORS Configuration**: Origin whitelisting

---

## Quality Gates

- **Location Page Limits**: 30 warning, 50 hard stop
- **Schema Deprecation Awareness**: FAQ/HowTo alerts
- **FID → INP Transition**: Updated Core Web Vitals
- **Thin Content Prevention**: Minimum quality thresholds
- **Index Bloat Safeguards**: Scale-appropriate limits

---

## Configuration

| Setting | Description |
|---------|-------------|
| `DEV_MODE` | Unlimited credits for development |
| `CREDITS_PER_DOLLAR` | Credit exchange rate (default: 8) |
| `MAX_PAGES` | Site audit page limit (500 max) |
| `SDK_WORKER_URL` | URL for the SDK worker service |
| `ENVIRONMENT` | deployment, production, or staging |

---

*Last updated: February 26, 2026*
