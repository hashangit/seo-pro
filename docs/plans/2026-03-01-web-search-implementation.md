# Web-Search MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace axios+cheerio scraping with agent-browser CLI for reliable Google search results.

**Architecture:** MCP server shells out to agent-browser CLI which launches headless Chromium. Uses spawn() with argument arrays for security, implements auto-install with fallback to manual instructions.

**Tech Stack:** TypeScript, Node.js child_process, agent-browser CLI, @modelcontextprotocol/sdk

---

## Task 1: Update Package Dependencies

**Files:**
- Modify: `web-search/package.json`

**Step 1: Remove axios and cheerio dependencies**

Remove these lines from `dependencies`:
```json
"@types/axios": "^0.14.4",
"@types/cheerio": "^0.22.35",
"axios": "^1.7.9",
"cheerio": "^1.0.0"
```

**Step 2: Verify package.json**

The dependencies section should now only have:
```json
"dependencies": {
  "@modelcontextprotocol/sdk": "0.6.0"
}
```

**Step 3: Commit**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && git add package.json && git commit -m "chore: remove axios and cheerio dependencies"
```

---

## Task 2: Create Utility Module

**Files:**
- Create: `web-search/src/utils.ts`

**Step 1: Create utils.ts with constants and types**

```typescript
import { spawn } from 'child_process';

export const MAX_QUERY_LENGTH = 500;
export const BROWSER_TIMEOUT_MS = 30000;
export const MAX_OUTPUT_SIZE = 10 * 1024 * 1024; // 10MB

export interface SearchResult {
  title: string;
  url: string;
  description: string;
}

export interface SearchResponse {
  results: SearchResult[];
  source: string;
  query: string;
}

export type ValidationResult =
  | { valid: true; query: string; limit: number }
  | { valid: false; error: string };

export type EnsureResult =
  | { ready: true }
  | { ready: false; instructions: string };
```

**Step 2: Add validateInput function**

```typescript
export function validateInput(query: unknown, limit: unknown): ValidationResult {
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
```

**Step 3: Add buildSearchUrl function**

```typescript
export function buildSearchUrl(query: string, limit: number): string {
  const url = new URL('https://www.google.com/search');
  url.searchParams.set('q', query);
  url.searchParams.set('num', limit.toString());
  return url.toString();
}
```

**Step 4: Add runCommand function**

```typescript
export async function runCommand(cmd: string, args: string[], timeout: number): Promise<string> {
  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';
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

    proc.stdout.on('data', (data) => {
      if (!killed) stdout += data;
    });

    proc.stderr.on('data', (data) => {
      if (!killed) stderr += data;
    });

    proc.on('close', (code) => {
      if (killed) return;
      cleanup();
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`Command failed: ${stderr || `exit code ${code}`}`));
      }
    });

    proc.on('error', (err: NodeJS.ErrnoException) => {
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
```

**Step 5: Commit**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && git add src/utils.ts && git commit -m "feat: add utility functions for web-search"
```

---

## Task 3: Create Agent-Browser Integration

**Files:**
- Create: `web-search/src/browser.ts`

**Step 1: Create browser.ts with imports**

```typescript
import {
  runCommand,
  BROWSER_TIMEOUT_MS,
  MAX_OUTPUT_SIZE,
  type SearchResult,
  type EnsureResult,
} from './utils.js';

export const AGENT_BROWSER_VERSION = 'latest';
export const INSTALL_TIMEOUT_MS = 60000;
export const CHROMIUM_INSTALL_TIMEOUT_MS = 120000;
```

**Step 2: Add runAgentBrowser function**

```typescript
export async function runAgentBrowser(args: string[], timeout: number = BROWSER_TIMEOUT_MS): Promise<string> {
  return runCommand('agent-browser', args, timeout);
}
```

**Step 3: Add ensureAgentBrowser function**

```typescript
export async function ensureAgentBrowser(): Promise<EnsureResult> {
  try {
    await runAgentBrowser(['--version'], 5000);
    return { ready: true };
  } catch {
    // Not installed - try auto-install
    try {
      await runCommand('pnpm', ['install', '-g', `agent-browser@${AGENT_BROWSER_VERSION}`], INSTALL_TIMEOUT_MS);
      await runCommand('agent-browser', ['install'], CHROMIUM_INSTALL_TIMEOUT_MS);
      return { ready: true };
    } catch {
      // Auto-install failed - return manual instructions
      return {
        ready: false,
        instructions: 'agent-browser auto-install failed. Install manually:\n' +
          '  pnpm install -g agent-browser@latest\n' +
          '  agent-browser install\n' +
          'Then restart the MCP server.',
      };
    }
  }
}
```

**Step 4: Add parseOutput function**

```typescript
export function parseOutput(stdout: string): unknown {
  if (stdout.length > MAX_OUTPUT_SIZE) {
    throw new Error(`Output too large: ${stdout.length} bytes exceeds limit of ${MAX_OUTPUT_SIZE} bytes`);
  }
  try {
    return JSON.parse(stdout);
  } catch {
    throw new Error('Invalid JSON output from agent-browser');
  }
}
```

**Step 5: Commit**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && git add src/browser.ts && git commit -m "feat: add agent-browser integration"
```

---

## Task 4: Create Search Result Extraction

**Files:**
- Create: `web-search/src/search.ts`

**Step 1: Create search.ts with imports**

```typescript
import { runAgentBrowser, ensureAgentBrowser, parseOutput } from './browser.js';
import { buildSearchUrl, type SearchResult, type SearchResponse } from './utils.js';

let browserReady = false;
```

**Step 2: Add extractResultsFromSnapshot function**

```typescript
interface SnapshotElement {
  role?: string;
  name?: string;
  url?: string;
  children?: SnapshotElement[];
}

function extractResultsFromSnapshot(snapshot: SnapshotElement[], limit: number): SearchResult[] {
  const results: SearchResult[] = [];

  function traverse(elements: SnapshotElement[]) {
    for (const el of elements) {
      if (results.length >= limit) return;

      // Google search results are typically links with URLs
      if (el.role === 'link' && el.url && el.name) {
        // Filter out Google's own navigation/ads
        if (el.url.startsWith('http') &&
            !el.url.includes('google.com/search') &&
            !el.url.includes('googleadservices.com')) {
          results.push({
            title: el.name,
            url: el.url,
            description: '', // Will try to get from sibling elements
          });
        }
      }

      if (el.children) {
        traverse(el.children);
      }
    }
  }

  traverse(snapshot);
  return results;
}
```

**Step 3: Add performSearch function**

```typescript
export async function performSearch(query: string, limit: number): Promise<SearchResponse> {
  // Check/install agent-browser if needed
  if (!browserReady) {
    const ensureResult = await ensureAgentBrowser();
    if (!ensureResult.ready) {
      throw new Error(ensureResult.instructions);
    }
    browserReady = true;
  }

  // Build search URL
  const searchUrl = buildSearchUrl(query, limit);

  // Open the search page
  await runAgentBrowser(['open', searchUrl]);

  // Get the accessibility tree snapshot as JSON
  const snapshotJson = await runAgentBrowser(['snapshot', '--json']);

  // Parse the snapshot
  const snapshot = parseOutput(snapshotJson);

  // Extract results from the snapshot
  let results: SearchResult[] = [];
  if (typeof snapshot === 'object' && snapshot !== null && 'snapshot' in snapshot) {
    const snapshotData = (snapshot as { snapshot: SnapshotElement[] }).snapshot;
    results = extractResultsFromSnapshot(snapshotData, limit);
  }

  return {
    results,
    source: 'google',
    query,
  };
}
```

**Step 4: Commit**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && git add src/search.ts && git commit -m "feat: add search result extraction from agent-browser snapshots"
```

---

## Task 5: Update Main Index File

**Files:**
- Modify: `web-search/src/index.ts`

**Step 1: Replace imports**

Replace:
```typescript
import axios from 'axios';
import * as cheerio from 'cheerio';
```

With:
```typescript
import { validateInput } from './utils.js';
import { performSearch } from './search.js';
```

**Step 2: Remove old interfaces and validation**

Remove these lines:
```typescript
interface SearchResult {
  title: string;
  url: string;
  description: string;
}

const isValidSearchArgs = (args: any): args is { query: string; limit?: number } =>
  typeof args === 'object' &&
  args !== null &&
  typeof args.query === 'string' &&
  (args.limit === undefined || typeof args.limit === 'number');
```

**Step 3: Update CallToolRequestSchema handler**

Replace the entire `this.server.setRequestHandler(CallToolRequestSchema, ...)` block with:

```typescript
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name !== 'search') {
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${request.params.name}`
        );
      }

      const args = request.params.arguments;
      const validation = validateInput(args?.query, args?.limit);

      if (!validation.valid) {
        throw new McpError(ErrorCode.InvalidParams, validation.error);
      }

      try {
        const response = await performSearch(validation.query, validation.limit);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(response.results, null, 2),
            },
          ],
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        return {
          content: [
            {
              type: 'text',
              text: `Search error: ${message}`,
            },
          ],
          isError: true,
        };
      }
    });
```

**Step 4: Remove performSearch method**

Delete the entire `performSearch` method (lines 121-152).

**Step 5: Commit**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && git add src/index.ts && git commit -m "refactor: update main server to use agent-browser"
```

---

## Task 6: Update README

**Files:**
- Modify: `web-search/README.md`

**Step 1: Update description and prerequisites**

Replace the existing README content with:

```markdown
# Web Search MCP Server

A Model Context Protocol (MCP) server that enables reliable web searching using agent-browser CLI with headless Chromium.

## Features

- Search the web using Google with real browser automation
- No API keys required
- Auto-installs agent-browser on first run (with manual fallback)
- Returns structured results with titles, URLs, and descriptions
- Configurable number of results per search

## Prerequisites

- Node.js 18+
- pnpm (recommended) or npm

The server will attempt to auto-install `agent-browser` on first run. If auto-install fails, you'll need to install manually:

```bash
pnpm install -g agent-browser@latest
agent-browser install
```

## Installation

1. Install dependencies:
```bash
pnpm install
```

2. Build the server:
```bash
pnpm build
```

3. Add the server to your MCP configuration:

For Claude Code (`~/.claude.json`):
```json
{
  "mcpServers": {
    "web-search": {
      "type": "stdio",
      "command": "node",
      "args": ["/path/to/web-search/build/index.js"]
    }
  }
}
```

## Usage

The server provides a single tool named `search`:

```typescript
{
  "query": string,    // Search query (1-500 characters)
  "limit": number     // Optional: Number of results (default: 5, max: 10)
}
```

Example:
```json
{
  "query": "hello world",
  "limit": 3
}
```

Response:
```json
[
  {
    "title": "Example Result",
    "url": "https://example.com",
    "description": "Description..."
  }
]
```

## Security

This server implements several security measures:
- Command injection prevention via spawn() with argument arrays
- URL encoding via Node.js URL API
- Input validation with length limits
- Output size limits (10MB max)
- Timeout handling with proper cleanup

## License

MIT
```

**Step 2: Commit**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && git add README.md && git commit -m "docs: update README for agent-browser implementation"
```

---

## Task 7: Build and Verify

**Step 1: Install dependencies**

```bash
cd /Users/hashanw/Developer/seo-pro/web-search && pnpm install
```

**Step 2: Build the project**

```bash
pnpm build
```

Expected: Build succeeds without errors.

**Step 3: Verify build output**

```bash
ls -la build/
```

Expected: `index.js` exists and is executable.

**Step 4: Final commit (if any changes)**

```bash
git status && git add -A && git commit -m "build: rebuild with agent-browser integration"
```

---

## Verification Checklist

After implementation, verify:

- [ ] `pnpm build` succeeds
- [ ] `build/index.js` exists
- [ ] No axios/cheerio imports in build output
- [ ] agent-browser --version check works
- [ ] Manual search test with agent-browser installed

## Rollback Plan

If issues arise:

```bash
cd /Users/hashanw/Developer/seo-pro/web-search
git log --oneline -5  # Find the commit before changes
git checkout <commit> -- src/ package.json README.md
pnpm install
pnpm build
```
