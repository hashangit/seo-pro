# SEO Pro

**SEO Pro** is a comprehensive SEO analysis platform that operates in two modes:

1. **SaaS Platform** - Full web application with credit-based pricing, user authentication, and dashboard
2. **Claude Code Skill** - CLI-based SEO analysis tool for Claude Code users

![SEO Pro Platform](screenshots/cover-image.jpeg)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)

---

## SaaS Platform

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js       │────▶│   FastAPI       │────▶│   SDK Worker    │
│   Frontend      │     │   Gateway       │     │   (Claude SDK)  │
│   (Vercel)      │     │   (Cloud Run)   │     │   (Cloud Run)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   Supabase      │     │   Cloud Tasks   │
                        │   PostgreSQL    │     │   (Queue)       │
                        └─────────────────┘     └─────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11+, Pydantic v2 |
| Auth | WorkOS AuthKit (SSO: Google, GitHub, etc.) |
| Database | Supabase PostgreSQL with Row-Level Security |
| AI Engine | Claude Agent SDK + GLM-4.7 (via Z.AI) |
| Deployment | Google Cloud Run, Cloud Tasks, Secret Manager |

### Credit Pricing

| Mode | Credits | Cost | Description |
|------|---------|------|-------------|
| Quick Analysis | 1 | ~$0.12 | Single analysis type (schema, technical, etc.) |
| Full Page Audit | 8 | ~$1.00 | All 12 analysis types on one page |
| Full Site Audit | 7/page | ~$0.88/page | Complete site-wide analysis |

**Exchange Rate:** $1 = 8 credits (never expire)

### Quick Start (SaaS)

```bash
# Clone and configure
git clone https://github.com/hashangit/seo-pro.git
cd seo-pro
cp .env.example .env

# Start local development
docker-compose up -d

# Access the platform
open http://localhost:3000     # Frontend
open http://localhost:8080     # API Gateway
```

### Analysis Types

The platform provides 12 comprehensive SEO analysis types:

| Type | Description |
|------|-------------|
| Technical SEO | Crawlability, indexability, Core Web Vitals |
| On-Page SEO | Meta tags, headings, keyword optimization |
| Content Quality | E-E-A-T signals, readability, depth |
| Schema Markup | JSON-LD validation and generation |
| Image Optimization | Alt text, compression, lazy loading |
| Internal Linking | Structure, anchor text, orphan pages |
| Sitemap Analysis | XML validation, URL coverage |
| AI Search (GEO) | Google AI Overviews, ChatGPT optimization |
| Competitor Analysis | Gap analysis, opportunity identification |
| Hreflang/i18n | Multi-language validation |
| Programmatic SEO | Scale analysis, thin content detection |
| Page Speed | Performance metrics, optimization tips |

---

## Claude Code Skill (CLI)

For Claude Code users, SEO Pro is available as a skill for in-terminal SEO analysis.

### Installation

```bash
# One-command install (Unix/macOS/Linux)
curl -fsSL https://raw.githubusercontent.com/hashangit/seo-pro/main/install.sh | bash

# Windows
irm https://raw.githubusercontent.com/hashangit/seo-pro/main/install.ps1 | iex
```

### CLI Commands

```bash
# Start Claude Code
claude

# Run a full site audit
/seo audit https://example.com

# Analyze a single page
/seo page https://example.com/about

# Check schema markup
/seo schema https://example.com

# Generate a sitemap
/seo sitemap generate

# Optimize for AI search
/seo geo https://example.com
```

| Command | Description |
|---------|-------------|
| `/seo audit <url>` | Full website audit with parallel subagent delegation |
| `/seo page <url>` | Deep single-page analysis |
| `/seo sitemap <url>` | Analyze existing XML sitemap |
| `/seo schema <url>` | Detect, validate, and generate Schema.org markup |
| `/seo images <url>` | Image optimization analysis |
| `/seo technical <url>` | Technical SEO audit |
| `/seo content <url>` | E-E-A-T and content quality analysis |
| `/seo geo <url>` | AI Overviews / Generative Engine Optimization |
| `/seo plan <type>` | Strategic SEO planning |
| `/seo hreflang <url>` | Hreflang/i18n audit and generation |

### CLI Demo

[Watch the full demo on YouTube](https://www.youtube.com/watch?v=COMnNlUakQk)

![SEO Audit Demo](screenshots/seo-audit-demo.gif)

---

## Features

### Core Web Vitals (2026 Metrics)
- **LCP** (Largest Contentful Paint): Target < 2.5s
- **INP** (Interaction to Next Paint): Target < 200ms
- **CLS** (Cumulative Layout Shift): Target < 0.1

### E-E-A-T Analysis
Based on September 2025 Quality Rater Guidelines:
- **Experience**: First-hand knowledge signals
- **Expertise**: Author credentials and depth
- **Authoritativeness**: Industry recognition
- **Trustworthiness**: Contact info, security, transparency

### AI Search Optimization (GEO)
Optimize for AI-powered search experiences:
- Google AI Overviews
- ChatGPT web search
- Perplexity
- Other generative AI engines

### Schema Markup Support
- Detection: JSON-LD (preferred), Microdata, RDFa
- Validation against Google's supported types
- Auto-generation with templates
- Video schema: VideoObject, BroadcastEvent, Clip

### Quality Gates
- Warning at 30+ location pages
- Hard stop at 50+ location pages
- Thin content detection
- Doorway page prevention

---

## Deployment

### Google Cloud Run

```bash
# Deploy gateway
gcloud run deploy seo-pro-gateway \
  --source ./deploy/Dockerfile.gateway \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,FRONTEND_URL=https://your-app.vercel.app" \
  --set-secrets "SUPABASE_SERVICE_KEY=supabase-service-key:latest"

# Deploy SDK worker
gcloud run deploy seo-pro-sdk-worker \
  --source ./deploy/Dockerfile.sdk-worker \
  --region us-central1 \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars "ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic" \
  --set-secrets "ANTHROPIC_AUTH_TOKEN=zai-api-key:latest"
```

See [Deployment Guide](docs/DEPLOYMENT.md) for complete instructions.

---

## Documentation

### SaaS Platform
- [Deployment Guide](docs/DEPLOYMENT.md) - Deploy to Google Cloud Run
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - Local development setup
- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [Features Overview](docs/FEATURES.md) - All 12 analysis types

### Claude Code Skill
- [Installation Guide](docs/INSTALLATION.md) - CLI setup
- [Commands Reference](docs/COMMANDS.md) - All available commands
- [MCP Integration](docs/MCP-INTEGRATION.md) - Connect Ahrefs, Semrush, etc.
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues

---

## Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Supabase account
- WorkOS account
- Google Cloud account (for deployment)

### Local Development

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Or use Docker Compose for everything
docker-compose up -d
```

### Testing

```bash
# Backend tests
pytest api/tests/ -v

# Frontend tests
cd frontend && npm test
```

---

## Security

- **SSRF Prevention**: URL validation blocks private IP ranges
- **Row-Level Security**: Supabase RLS isolates data per user
- **JWT Authentication**: WorkOS token validation with audience verification
- **CORS Configuration**: Origin whitelisting for API access
- **Input Sanitization**: Injection prevention across all endpoints
- **Secret Management**: Google Secret Manager for production

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.11+ |
| Node.js | 20+ |
| Claude Code CLI | Latest (for skill mode) |
| Playwright | Optional, for screenshots |

---

## Uninstall (CLI Skill)

```bash
curl -fsSL https://raw.githubusercontent.com/hashangit/seo-pro/main/uninstall.sh | bash
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contributing

Contributions welcome! Please read the guidelines in `docs/` before submitting PRs.

---

Built for Claude Code by [@hashangit](https://github.com/hashangit)
