# Architecture

## Overview

SEO Pro uses the Claude Agent SDK for unified cloud-based SEO analysis, leveraging filesystem-based Skills and Agents for multi-agent orchestration.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SEO PRO ARCHITECTURE                                │
│                                                                                  │
│  ┌─────────────────┐                                                            │
│  │   FRONTEND      │                     ┌─────────────────────────────────────┐│
│  │   (Next.js)     │──────► REST ───────►│          API GATEWAY               ││
│  │                 │◄───── JSON ────────│          (FastAPI)                  ││
│  │  - Thin Client  │                     │                                     ││
│  │  - WorkOS Auth  │                     │  - Authentication (WorkOS JWT)      ││
│  └─────────────────┘                     │  - Credit Management (Supabase)     ││
│                                          │  - Cloud Tasks submission           ││
│                                          │  - Routes to SDK Worker             ││
│                                          └───────────┬─────────────────────────┘│
│                                                      │                          │
│                                                      │ Cloud Tasks              │
│                                                      │ (sdk-worker-queue)       │
│                                                      ▼                          │
│                             ┌────────────────────────────────────────────────┐  │
│                             │              SDK WORKER                        │  │
│                             │                                                │  │
│                             │  Claude Agent SDK                              │  │
│                             │  ┌──────────────────────────────────────────┐  │  │
│                             │  │ Skills/Agents from filesystem:           │  │  │
│                             │  │ • skills/seo/SKILL.md (orchestrator)     │  │  │
│                             │  │ • skills/seo-audit/SKILL.md              │  │  │
│                             │  │ • agents/seo-technical.md                │  │  │
│                             │  │ • agents/seo-content.md                  │  │  │
│                             │  │ • agents/seo-schema.md                   │  │  │
│                             │  │ • agents/seo-visual.md                   │  │  │
│                             │  │ • agents/seo-performance.md              │  │  │
│                             │  │ • agents/seo-sitemap.md                  │  │  │
│                             │  └──────────────────────────────────────────┘  │  │
│                             │                                                │  │
│                             │  ┌──────────────────────────────────────────┐  │  │
│                             │  │ Built-in Tools:                          │  │  │
│                             │  │ • Bash → scripts/*.py                    │  │  │
│                             │  │ • Read/Write → file operations           │  │  │
│                             │  │ • Task → subagent delegation             │  │  │
│                             │  │ • Playwright MCP → browser automation    │  │  │
│                             │  └──────────────────────────────────────────┘  │  │
│                             │                                                │  │
│                             │  ALL analysis in ONE service:                  │  │
│                             │  ✓ Technical, Content, Schema (via Bash)      │  │
│                             │  ✓ Visual, Performance (via Playwright MCP)   │  │
│                             │                                                │  │
│                             └────────────────────────────────────────────────┘  │
│                                                                                  │
│                             ┌────────────────────────────────────────────────┐  │
│                             │           SUPABASE                             │  │
│                             │           - Users, Credits, Audits, Tasks      │  │
│                             └────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
project-root/
├── skills/                       # Skills directory (loaded by SDK)
│   ├── seo/                      # Main orchestrator skill
│   │   └── SKILL.md              # Entry point with routing logic
│   │
│   ├── seo-audit/                # Full site audit
│   │   └── SKILL.md
│   ├── seo-competitor-pages/     # Competitor comparison pages
│   │   └── SKILL.md
│   ├── seo-content/              # E-E-A-T analysis
│   │   └── SKILL.md
│   ├── seo-geo/                  # AI search optimization
│   │   └── SKILL.md
│   ├── seo-hreflang/             # Hreflang/i18n SEO
│   │   └── SKILL.md
│   ├── seo-images/               # Image optimization
│   │   └── SKILL.md
│   ├── seo-page/                 # Single page analysis
│   │   └── SKILL.md
│   ├── seo-plan/                 # Strategic planning
│   │   ├── SKILL.md
│   │   └── assets/               # Industry templates
│   │       ├── saas.md
│   │       ├── ecommerce.md
│   │       ├── local-service.md
│   │       ├── publisher.md
│   │       └── agency.md
│   ├── seo-programmatic/         # Programmatic SEO
│   │   └── SKILL.md
│   ├── seo-schema/               # Schema markup
│   │   └── SKILL.md
│   ├── seo-sitemap/              # Sitemap analysis/generation
│   │   └── SKILL.md
│   └── seo-technical/            # Technical SEO
│       └── SKILL.md
│
├── agents/                       # Subagents directory (loaded by SDK)
│   ├── seo-technical.md          # Technical SEO specialist
│   ├── seo-content.md            # Content quality reviewer
│   ├── seo-schema.md             # Schema markup expert
│   ├── seo-sitemap.md            # Sitemap architect
│   ├── seo-performance.md        # Performance analyzer
│   └── seo-visual.md             # Visual analyzer
│
├── seo/                          # Alternative skill location
│   └── SKILL.md                  # Main SEO orchestrator
│
├── workers/
│   └── sdk_worker.py             # SDK-based unified worker
│
├── scripts/
│   ├── fetch_page.py             # Page fetching utility
│   ├── parse_html.py             # HTML parsing utility
│   └── capture_screenshot.py     # Screenshot utility
│
├── api/
│   └── main.py                   # API Gateway (FastAPI)
│
└── frontend/
    └── lib/api.ts                # Frontend API client
```

## Component Types

### Skills

Skills are markdown files with YAML frontmatter that define capabilities and instructions.

**SKILL.md Format:**
```yaml
---
name: skill-name
description: >
  When to use this skill. Include activation keywords
  and concrete use cases.
---

# Skill Title

Instructions and documentation...
```

### Subagents

Subagents are specialized workers that can be delegated tasks. They have their own context and tools.

**Agent Format:**
```yaml
---
name: agent-name
description: What this agent does.
tools: Read, Bash, Write, Glob, Grep
---

Instructions for the agent...
```

### Reference Files

Reference files contain static data loaded on-demand to avoid bloating the main skill.

## Orchestration Flow

### Full Audit (`/seo audit`)

```
User Request
    │
    ▼
┌─────────────────┐
│   seo       │  ← Main orchestrator
│   (SKILL.md)    │
└────────┬────────┘
         │
         │  Detects business type
         │  Spawns subagents in parallel
         │
    ┌────┴────┬────────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│tech   │ │content│ │schema │ │sitemap│ │perf   │ │visual │
│agent  │ │agent  │ │agent  │ │agent  │ │agent  │ │agent  │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │        │        │        │        │
    └─────────┴────────┴────┬───┴────────┴────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Aggregate    │
                    │  Results      │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Generate     │
                    │  Report       │
                    └───────────────┘
```

### Individual Command

```
User Request (e.g., /seo page)
    │
    ▼
┌─────────────────┐
│   seo       │  ← Routes to sub-skill
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   seo-page      │  ← Sub-skill handles directly
│   (SKILL.md)    │
└─────────────────┘
```

## Design Principles

### 1. Progressive Disclosure

- Main SKILL.md is concise (<200 lines)
- Reference files loaded on-demand
- Detailed instructions in sub-skills

### 2. Parallel Processing

- Subagents run concurrently during audits
- Independent analyses don't block each other
- Results aggregated after all complete

### 3. Quality Gates

- Built-in thresholds prevent bad recommendations
- Location page limits (30 warning, 50 hard stop)
- Schema deprecation awareness
- FID → INP replacement enforced

### 4. Industry Awareness

- Templates for different business types
- Automatic detection from homepage signals
- Tailored recommendations per industry

### 5. SDK-Based Orchestration

- Claude Agent SDK loads Skills/Agents from filesystem
- No Python orchestration code needed
- Same multi-agent reasoning as CLI

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Skill | `seo-{name}/SKILL.md` | `seo-audit/SKILL.md` |
| Agent | `seo-{name}.md` | `seo-technical.md` |
| Reference | `{topic}.md` | `cwv-thresholds.md` |
| Script | `{action}_{target}.py` | `fetch_page.py` |
| Template | `{industry}.md` | `saas.md` |

## Playwright CLI Integration

### Why Playwright CLI

| Aspect | Playwright MCP | Playwright CLI |
|--------|---------------|----------------|
| Token usage | Loads large tool schemas into context | Concise commands via Bash |
| Integration | Requires MCP server config | Same as scripts (Bash) |
| State | Persistent browser context | Session-based, can persist |
| Fit | Long-running autonomous workflows | High-throughput coding agents |

### Key Playwright CLI Commands for SEO

| Command | Purpose |
|---------|---------|
| `playwright-cli open <url>` | Navigate to URL |
| `playwright-cli snapshot` | Get page snapshot (element refs) |
| `playwright-cli screenshot` | Capture screenshot |
| `playwright-cli console` | Get console logs/errors |
| `playwright-cli network` | Get network requests |
| `playwright-cli eval "<js>"` | Evaluate JavaScript (CWV metrics) |
| `playwright-cli resize 375 812` | Test mobile viewport |
| `playwright-cli -s=name open <url>` | Named session for isolation |

### Agent Examples with Playwright CLI

**seo-visual.md:**
```markdown
---
name: seo-visual
description: Visual SEO analyzer. Screenshots, mobile rendering, above-fold analysis.
tools: Bash, Read, Write
---

You are a Visual SEO specialist. Use Playwright CLI via Bash:

1. Open URL: `playwright-cli open <url>`
2. Capture screenshot: `playwright-cli screenshot --filename=desktop.png`
3. Test mobile: `playwright-cli resize 375 812 && playwright-cli screenshot --filename=mobile.png`
4. Get page snapshot: `playwright-cli snapshot`
5. Close: `playwright-cli close`

Output: Visual issues, mobile problems, layout concerns.
```

**seo-performance.md:**
```markdown
---
name: seo-performance
description: Performance analyzer. LCP, INP, CLS measurements via browser.
tools: Bash, Read, Write
---

You are a Performance SEO specialist. Use Playwright CLI via Bash:

1. Open URL: `playwright-cli open <url>`
2. Get network requests: `playwright-cli network`
3. Get console errors: `playwright-cli console error`
4. Evaluate CWV metrics:
   ```
   playwright-cli eval "JSON.stringify({
     lcp: performance.getEntriesByType('largest-contentful-paint').slice(-1)[0]?.startTime,
     cls: performance.getEntriesByType('layout-shift').reduce((a,e)=>a+e.value,0)
   })"
   ```
5. Close: `playwright-cli close`

Output: LCP, INP, CLS scores, performance recommendations.
```

## Cloud Tasks Queue

| Queue | Purpose |
|-------|---------|
| `sdk-worker-queue` | Routes to SDK Worker |

## SDK Worker Implementation

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

@app.post("/analyze")
async def analyze_endpoint(request: AnalyzeRequest):
    """Run SEO audit using Claude Agent SDK with filesystem Skills."""

    async for message in query(
        prompt=f"Run a full SEO audit on {request.url}",
        options=ClaudeAgentOptions(
            cwd="/app",
            setting_sources=["project"],
            allowed_tools=["Skill", "Task", "Bash", "Read", "Write", "Glob", "Grep"],
            permission_mode="bypassPermissions",
        ),
    ):
        if hasattr(message, "result"):
            return {"result": message.result}
        elif hasattr(message, "content"):
            yield message
```

## Container Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Node.js (required by Claude Agent SDK for CLI)
RUN apt-get update && apt-get install -y nodejs npm

# Install Claude Code CLI (required by SDK)
RUN npm install -g @anthropic-ai/claude-code

# Install Playwright CLI globally
RUN npm install -g @playwright/cli@latest

# Install Playwright browsers
RUN playwright-cli install chromium

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project with skills and agents
COPY . /app
WORKDIR /app

# Run worker
CMD ["python", "-m", "workers.sdk_worker"]
```

## Extension Points

### Adding a New Sub-Skill

1. Create `skills/seo-newskill/SKILL.md`
2. Add YAML frontmatter with name and description
3. Write skill instructions
4. Update main `seo/SKILL.md` to route to new skill
5. Add corresponding endpoint in `api/main.py` and `workers/sdk_worker.py`

### Adding a New Subagent

1. Create `agents/seo-newagent.md`
2. Add YAML frontmatter with name, description, tools
3. Write agent instructions
4. Reference from relevant skills

### Adding a New Reference File

1. Create file in appropriate `assets/` directory within the skill
2. Reference in skill with load-on-demand instruction

## What the SDK Handles

- Loading the `seo-audit` skill from `skills/`
- Calling `scripts/fetch_page.py` via Bash when the skill instructs
- Using Playwright MCP tools for browser automation
- Delegating to `seo-technical`, `seo-content`, etc. subagents
- Synthesizing results with Claude
- Generating the SEO Health Score and Action Plan

## API Endpoints

### Individual Analysis Endpoints

| Endpoint | CLI Equivalent | Description |
|----------|---------------|-------------|
| `POST /api/v1/analyze/page` | `/seo page` | Comprehensive single-page analysis (all-in-one) |
| `POST /api/v1/analyze/technical` | `/seo technical` | Technical SEO analysis |
| `POST /api/v1/analyze/content` | `/seo content` | E-E-A-T content analysis |
| `POST /api/v1/analyze/schema` | `/seo schema` | Schema markup analysis |
| `POST /api/v1/analyze/geo` | `/seo geo` | AI search optimization |
| `POST /api/v1/analyze/sitemap` | `/seo sitemap` | Sitemap analysis |
| `POST /api/v1/analyze/hreflang` | `/seo hreflang` | International SEO |
| `POST /api/v1/analyze/images` | `/seo images` | Image optimization |
| `POST /api/v1/analyze/visual` | `/seo visual` | Visual analysis |
| `POST /api/v1/analyze/performance` | `/seo performance` | Core Web Vitals |
| `POST /api/v1/analyze/plan` | `/seo plan` | Strategic SEO planning |
| `POST /api/v1/analyze/programmatic` | `/seo programmatic` | Programmatic SEO |
| `POST /api/v1/analyze/competitor-pages` | `/seo competitor-pages` | Competitor comparison page analysis (SEO/GEO/AEO) |

### Audit Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/audit/estimate` | Get audit cost estimate |
| `POST /api/v1/audit/run` | Run full audit |
| `GET /api/v1/audit/{id}` | Get audit status/results |
| `GET /api/v1/audit` | List user's audits |

## Key Components

| Component | Purpose |
|-----------|---------|
| API Gateway | Authentication, credit management, Cloud Tasks submission |
| SDK Worker | Loads Skills/Agents, orchestrates analysis via Claude Agent SDK |
| Scripts | Called by SDK via Bash for page fetching, parsing, etc. |
| Skills/Agents | Loaded by SDK for multi-agent SEO analysis |
| Supabase | Users, credits, audits, tasks storage |
