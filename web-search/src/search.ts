import { runAgentBrowser, ensureAgentBrowser, parseOutput } from './browser.js';
import { buildSearchUrl, type SearchResult, type SearchResponse } from './utils.js';

let browserReady = false;

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
