# Web-Search MCP Server Design

**Date:** 2026-03-01
**Status:** Approved
**Author:** Claude + User

## Overview

Replace the current axios+cheerio web scraping implementation with `agent-browser` CLI for reliable Google search results. The current implementation fails when Google serves JavaScript challenge pages.

## Problem Statement

- Current: HTTP-based scraping with axios + cheerio
- Issue: Google/DuckDuckGo block scrapers with JS challenges
- Solution: Use real browser automation via agent-browser CLI

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│  web-search MCP  │────▶│  agent-browser  │
│  (Claude Code)  │     │     server       │     │     (CLI)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌──────────────┐        ┌─────────────┐
                        │ Auto-install │        │  Chromium   │
                        │   via pnpm   │        │  (headless) │
                        │   (fallback) │        └─────────────┘
                        └──────────────┘
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Browser automation | agent-browser CLI | Purpose-built for AI agents, JSON output |
| Installation | Auto-install with fallback | Better UX, graceful degradation |
| Package manager | pnpm | User preference |
| Search engine | Google | Most comprehensive results |

## Tool Interface

**Input:**
```typescript
{
  query: string,      // Search query (1-500 chars)
  limit?: number      // Max results (default: 5, max: 10)
}
```

**Output:**
```json
{
  "results": [
    { "title": "...", "url": "...", "description": "..." }
  ],
  "source": "google",
  "query": "original query"
}
```

## Security Measures

| Measure | Implementation |
|---------|----------------|
| Command injection | `spawn()` with argument arrays |
| URL injection | URL API with auto-encoding |
| Timeout races | `killed` flag with proper cleanup |
| Binary not found | ENOENT detection with helpful message |
| Output limits | 10MB max |
| JSON errors | Try/catch with clear errors |
| Input validation | Length limits (1-500 chars) |

## Implementation

```typescript
import { spawn } from 'child_process';
import { URL } from 'url';

const MAX_QUERY_LENGTH = 500;
const BROWSER_TIMEOUT_MS = 30000;
const MAX_OUTPUT_SIZE = 10 * 1024 * 1024; // 10MB

// Input validation with sanitization
function validateInput(query: unknown, limit: unknown): { valid: true; query: string; limit: number } | { valid: false; error: string } {
  if (typeof query !== 'string' || query.length === 0) {
    return { valid: false, error: 'Query must be a non-empty string' };
  }
  // Sanitize control characters
  const sanitized = query.replace(/[\x00-\x1F\x7F]/g, '');
  if (sanitized.length === 0) {
    return { valid: false, error: 'Query contains only control characters' };
  }
  if (sanitized.length > MAX_QUERY_LENGTH) {
    return { valid: false, error: `Query too long (max ${MAX_QUERY_LENGTH} chars)` };
  }
  const limitNum = typeof limit === 'number' ? Math.min(Math.max(1, limit), 10) : 5;
  return { valid: true, query: sanitized, limit: limitNum };
}

// Safe URL construction
function buildSearchUrl(query: string, limit: number): string {
  const url = new URL('https://www.google.com/search');
  url.searchParams.set('q', query);
  url.searchParams.set('num', limit.toString());
  return url.toString();
}

// Generic command runner
async function runCommand(cmd: string, args: string[], timeout: number): Promise<string> {
  return new Promise((resolve, reject) => {
    let stdout = '', stderr = '';
    let killed = false;

    const proc = spawn(cmd, args);

    const cleanup = () => {
      clearTimeout(timer);
      proc.removeAllListeners();
    };

    const timer = setTimeout(() => {
      killed = true;
      proc.kill('SIGTERM');
      cleanup();
      reject(new Error(`Command timeout after ${timeout}ms`));
    }, timeout);

    proc.stdout.on('data', (data) => { if (!killed) stdout += data; });
    proc.stderr.on('data', (data) => { if (!killed) stderr += data; });

    proc.on('close', (code) => {
      if (killed) return;
      cleanup();
      if (code === 0) resolve(stdout);
      else reject(new Error(`Command failed: ${stderr || `exit code ${code}`}`));
    });

    proc.on('error', (err) => {
      if (killed) return;
      cleanup();
      if (err.code === 'ENOENT') {
        reject(new Error(`Command not found: ${cmd}. Please ensure it is installed.`));
      } else {
        reject(err);
      }
    });
  });
}

// Run agent-browser command
async function runAgentBrowser(args: string[], timeout: number = BROWSER_TIMEOUT_MS): Promise<string> {
  return runCommand('agent-browser', args, timeout);
}

// Output parsing with size limits
function parseOutput(stdout: string): any {
  if (stdout.length > MAX_OUTPUT_SIZE) {
    throw new Error(`Output too large: ${stdout.length} bytes exceeds limit of ${MAX_OUTPUT_SIZE} bytes`);
  }
  try {
    return JSON.parse(stdout);
  } catch {
    throw new Error('Invalid JSON output from agent-browser');
  }
}

// Install check with auto-install attempt, then fallback to manual instructions
async function ensureAgentBrowser(): Promise<{ ready: true } | { ready: false; instructions: string }> {
  try {
    await runAgentBrowser(['--version'], 5000);
    return { ready: true };
  } catch {
    // Not installed - try auto-install
    try {
      await runCommand('pnpm', ['install', '-g', 'agent-browser@latest'], 60000);
      await runCommand('agent-browser', ['install'], 120000);
      return { ready: true };
    } catch {
      // Auto-install failed - return manual instructions
      return {
        ready: false,
        instructions: 'agent-browser auto-install failed. Install manually:\n' +
          '  pnpm install -g agent-browser@latest\n' +
          '  agent-browser install\n' +
          'Then restart the MCP server.'
      };
    }
  }
}
```

## Flow

1. MCP server receives `search` tool call
2. Validate input (query length 1-500, limit 1-10)
3. Build safe URL using URL API with auto-encoding
4. Ensure agent-browser is available (check → auto-install → manual fallback)
5. Spawn agent-browser safely: `['open', searchUrl]` then `['snapshot', '--json']`
6. Parse JSON output with size limits
7. Extract search results from accessibility tree
8. Return structured results

## Dependencies

- `agent-browser` CLI (external, auto-installed or manual)
- Node.js built-in: `child_process`, `url`
- Existing: `@modelcontextprotocol/sdk`

## Testing Checklist

- [ ] Command injection attempts blocked
- [ ] URL injection attempts blocked
- [ ] Timeout handling works correctly
- [ ] ENOENT errors produce helpful messages
- [ ] Output size limits enforced
- [ ] Invalid JSON handled gracefully
- [ ] Auto-install flow works
- [ ] Manual fallback instructions clear

## Migration Plan

1. Backup existing `src/index.ts`
2. Replace with new implementation
3. Update `package.json` if needed
4. Test with manual agent-browser install first
5. Test auto-install flow
6. Update README with new prerequisites

## Review History

| Date | Reviewer | Result |
|------|----------|--------|
| 2026-03-01 | senior-code-reviewer | Conditionally Approved |
