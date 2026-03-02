import {
  runCommand,
  BROWSER_TIMEOUT_MS,
  MAX_OUTPUT_SIZE,
  type EnsureResult,
} from './utils.js';

export const AGENT_BROWSER_VERSION = 'latest';
export const INSTALL_TIMEOUT_MS = 60000;
export const CHROMIUM_INSTALL_TIMEOUT_MS = 120000;

export async function runAgentBrowser(args: string[], timeout: number = BROWSER_TIMEOUT_MS): Promise<string> {
  return runCommand('agent-browser', args, timeout);
}

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
