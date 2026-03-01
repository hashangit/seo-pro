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
