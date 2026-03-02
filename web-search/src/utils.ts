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

export function buildSearchUrl(query: string, limit: number): string {
  const url = new URL('https://www.google.com/search');
  url.searchParams.set('q', query);
  url.searchParams.set('num', limit.toString());
  return url.toString();
}

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
