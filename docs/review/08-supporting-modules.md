# 08 — Supporting Modules

## Web Search MCP Server (`web-search/`)

A **Model Context Protocol (MCP) server** that provides web search capability via Google without API keys.

### Architecture

```
Claude Code / MCP Client
        │
        ▼ (stdio JSON-RPC)
┌───────────────────────────┐
│  web-search/src/index.ts  │  MCP Server
│  (MCP SDK 0.6.0)         │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  web-search/src/search.ts │  Search logic
│  web-search/src/browser.ts│  agent-browser integration
│  web-search/src/utils.ts  │  Validation + command runner
└───────────┬───────────────┘
            │
            ▼
     agent-browser CLI
     (headless Chromium)
            │
            ▼
      Google Search
```

### Key Files

| File | Purpose |
|------|---------|
| `src/index.ts` | MCP server with `search` tool definition + handler |
| `src/search.ts` | `performSearch()` — opens Google, takes accessibility snapshot, extracts results |
| `src/browser.ts` | `runAgentBrowser()`, `ensureAgentBrowser()` auto-install, `parseOutput()` |
| `src/utils.ts` | Input validation, search URL builder, `spawn()`-based command runner |

### Tool Definition

```typescript
{
  name: "search",
  parameters: {
    query: string (1-500 chars),
    limit: number (1-10, default: 5)
  }
}
```

### Security Measures

- Command injection prevention via `spawn()` with argument arrays
- URL encoding via `new URL()`
- Input validation with length limits, control character stripping
- Output size limits (10MB max)
- Timeout handling with SIGTERM + proper cleanup

### Dependencies

- `@modelcontextprotocol/sdk` 0.6.0
- TypeScript 5.3+ compiled to ESM
- `agent-browser` CLI (auto-installed or manual fallback)

## Hooks (`hooks/`)

Claude Code automation hooks for SEO quality enforcement.

### `pre-commit-seo-check.sh`

Bash script triggered on `PreToolUse` with matcher `Bash`. Runs on all staged HTML-like files:

| Check | Severity | Exit Code |
|-------|----------|-----------|
| Placeholder text in schema | Error (block) | 2 |
| Title tag length < 30 or > 70 | Warning | 0 |
| Images without alt text | Warning | 0 |
| Deprecated schema types (HowTo, SpecialAnnouncement) | Error (block) | 2 |
| FID references (should be INP) | Warning | 0 |
| Meta description < 120 or > 160 | Warning | 0 |

Staged file detection via `git diff --cached`. Supports `.html, .htm, .php, .jsx, .tsx, .vue, .svelte`.

### `validate-schema.py`

Python script triggered on `PostToolUse` with matcher `Edit|Write`. Validates JSON-LD blocks in edited files:

| Check | Severity |
|-------|----------|
| Invalid JSON | Error |
| Missing @context | Error |
| Missing @type | Error |
| Placeholder text ([Business Name], [City], etc.) | Critical (blocks) |
| Deprecated types (HowTo, SpecialAnnouncement, ClaimReview, etc.) | Critical (blocks) |
| Restricted types (FAQPage) | Warning |

Output: Warnings print to stdout, critical errors cause exit code 2 (blocks the edit).

## PDF Reference (`pdf/google-seo-reference.md`)

A concise Google SEO quick reference document (February 2026 edition). Used as a knowledge base for subagents:

- How Google Search Works (crawling → indexing → serving)
- Google Search Essentials (technical, spam policies, best practices)
- E-E-A-T framework with Dec 2025 update notes
- Core Web Vitals thresholds (LCP, INP, CLS)
- Structured data best practices + deprecated/restricted types
- Common penalties and recovery steps
- Official documentation links
- Mobile-first indexing note (100% complete since July 2024)

## Schema Templates (`schema/templates.json`)

9 JSON-LD schema templates for common use cases:

| Template | Purpose |
|----------|---------|
| `VideoObject` | Video content with thumbnail, duration, publisher |
| `BroadcastEvent` | Live streaming with LIVE badge eligibility |
| `Clip` | Key moments/chapters with timestamps |
| `SeekToAction` | Seek functionality in video rich results |
| `SoftwareSourceCode` | GitHub repos with language, license, dates |
| `ProductGroup` | E-commerce variants (size, color) with variesBy |
| `ProfilePage` | Author profiles for E-E-A-T signals |
| `Certification` | Product certifications (Energy Star, etc.) |
| `OfferShippingDetails` | Shipping rates + delivery time for e-commerce |

Each template includes placeholder values (`[Video Title]`, `[YYYY-MM-DD]`, etc.) and a description of when to use it.

## Install/Uninstall Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `install.sh` | Unix/macOS/Linux | One-command CLI skill install |
| `install.ps1` | Windows | PowerShell install script |
| `uninstall.sh` | Unix/macOS/Linux | CLI skill removal |

These copy the skills, agents, scripts, hooks, and references into the user's Claude Code skills directory (`~/.claude/skills/seo/`).

## Existing Documentation (`docs/`)

| File | Content |
|------|---------|
| `ARCHITECTURE.md` | System design and components |
| `DEPLOYMENT.md` | Deploy to Google Cloud Run |
| `DEVELOPER_GUIDE.md` | Local development setup |
| `FEATURES.md` | All 12 analysis types |
| `INSTALLATION.md` | CLI setup guide |
| `COMMANDS.md` | All available slash commands |
| `MCP-INTEGRATION.md` | Ahrefs, Semrush, etc. |
| `LOCAL_DEVELOPMENT.md` | Local dev environment |
| `RATE-LIMITING.md` | Rate limiting configuration |
| `TODO.md` | Infrastructure improvements tracker |
| `TROUBLESHOOTING.md` | Common issues |
| `plans/` | Planning documents |
