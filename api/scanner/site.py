"""
Site Scanner - Fast HTTP-based page count estimation.
No Playwright, no heavy processing. Used for cost estimation.
"""

import asyncio
import base64
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# Security: Import URL validator to prevent SSRF attacks
from api.utils.url_validator import validate_url_safe, normalize_url


# Maximum content size to prevent DoS (10MB)
MAX_CONTENT_SIZE = 10 * 1024 * 1024

# Maximum URLs to process from sitemap (prevent XML bomb attacks)
MAX_SITEMAP_URLS = 10000


class SiteScanner:
    """
    Fast HTTP-based scanner to estimate page count.

    Strategy:
    1. Try robots.txt for sitemap URL
    2. Parse sitemap XML to count URLs
    3. Fallback: estimate from homepage internal links
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "SEO Pro/1.0 (+https://seopro.example.com/bot)"
                }
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def estimate_pages(self, url: str) -> dict:
        """
        Estimate page count for a URL.

        Returns:
            {
                "page_count": int,
                "confidence": float (0.0-1.0),
                "source": str ("sitemap", "homepage", "default")
            }
        """
        try:
            # Security: Validate URL to prevent SSRF attacks
            is_valid, error_msg = validate_url_safe(url)
            if not is_valid:
                return {
                    "page_count": 1,
                    "confidence": 0.0,
                    "source": "default",
                    "error": f"URL validation failed: {error_msg}"
                }

            # Normalize URL
            url = normalize_url(url)
            parsed = urlparse(url)

            # Try sitemap first (most accurate)
            sitemap_url = await self._find_sitemap(url)
            if sitemap_url:
                result = await self._count_sitemap_urls(sitemap_url)
                if result["page_count"] > 0:
                    return result

            # Fallback: estimate from homepage
            return await self._estimate_from_homepage(url)

        except Exception as e:
            # Conservative default estimate on any error
            return {"page_count": 1, "confidence": 0.5, "source": "default", "error": str(e)}

    async def _find_sitemap(self, url: str) -> Optional[str]:
        """Find sitemap URL from robots.txt or common locations."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            client = await self._get_client()
            response = await client.get(robots_url)
            if response.status_code == 200:
                # Parse robots.txt for Sitemap directive
                for line in response.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith("sitemap:"):
                        sitemap = line.split(":", 1)[1].strip()
                        return sitemap
        except Exception:
            pass

        # Try common sitemap locations
        common_paths = ["/sitemap.xml", "/sitemaps.xml", "/sitemap_index.xml"]

        for path in common_paths:
            try:
                client = await self._get_client()
                test_url = f"{parsed.scheme}://{parsed.netloc}{path}"
                response = await client.head(test_url)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()

                    # Check if it's actually XML
                    if "xml" in content_type or "text" in content_type:
                        return test_url

            except Exception:
                continue

        return None

    async def _count_sitemap_urls(self, sitemap_url: str) -> dict:
        """Count URLs in sitemap XML with size limits to prevent DoS."""
        client = await self._get_client()

        try:
            # Security: Check content-length first to prevent DoS
            head_response = await client.head(sitemap_url)
            content_length = int(head_response.headers.get("content-length", 0))
            if content_length > MAX_CONTENT_SIZE:
                return {
                    "page_count": MAX_SITEMAP_URLS,
                    "confidence": 0.8,
                    "source": "sitemap",
                    "warning": "Sitemap too large, using maximum estimate"
                }

            response = await client.get(sitemap_url)
            response.raise_for_status()

            # Security: Limit response size
            if len(response.content) > MAX_CONTENT_SIZE:
                return {
                    "page_count": MAX_SITEMAP_URLS,
                    "confidence": 0.8,
                    "source": "sitemap",
                    "warning": "Sitemap response too large, using maximum estimate"
                }

            # Check if it's a sitemap index
            if "<sitemapindex" in response.text.lower():
                return await self._count_sitemap_index(sitemap_url, response.text)

            # Regular sitemap
            urls = self._extract_urls_from_xml(response.text)
            # Security: Cap at maximum
            url_count = min(len(urls), MAX_SITEMAP_URLS)
            return {
                "page_count": url_count,
                "confidence": 1.0,
                "source": "sitemap"
            }

        except Exception as e:
            return {"page_count": 1, "confidence": 0.5, "source": "sitemap", "error": str(e)}

    async def _count_sitemap_index(self, sitemap_url: str, index_text: str) -> dict:
        """Count URLs from a sitemap index (references other sitemaps)."""
        client = await self._get_client()
        soup = BeautifulSoup(index_text, "xml")

        # Find all sitemap locations
        sitemap_locs = [loc.text for loc in soup.find_all("loc") if "sitemap" in loc.name.lower()]

        if not sitemap_locs:
            return {"page_count": 1, "confidence": 0.5, "source": "sitemap"}

        # Security: Limit sub-sitemaps to prevent DoS
        all_urls = []
        tasks = []

        for loc in sitemap_locs[:10]:  # Limit for performance
            tasks.append(self._fetch_sitemap_urls(loc))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_urls.extend(result)

        # Security: Cap at maximum
        url_count = min(len(all_urls), MAX_SITEMAP_URLS)
        return {
            "page_count": url_count,
            "confidence": 1.0,
            "source": "sitemap"
        }

    async def _fetch_sitemap_urls(self, sitemap_url: str) -> list:
        """Fetch and extract URLs from a single sitemap."""
        try:
            client = await self._get_client()
            # Security: Check content-length first
            head_response = await client.head(sitemap_url)
            content_length = int(head_response.headers.get("content-length", 0))
            if content_length > MAX_CONTENT_SIZE:
                return []

            response = await client.get(sitemap_url)
            response.raise_for_status()
            return self._extract_urls_from_xml(response.text)
        except Exception:
            return []

    def _extract_urls_from_xml(self, xml_text: str) -> list:
        """Extract all URLs from sitemap XML."""
        soup = BeautifulSoup(xml_text, "xml")
        urls = []

        # URL elements can be <url><loc> or <loc> directly
        for loc in soup.find_all("loc"):
            if loc.parent and loc.parent.name == "url":
                urls.append(loc.text)
            elif loc.parent.name not in ["sitemap", "sitemapindex"]:
                urls.append(loc.text)

        return urls

    async def _estimate_from_homepage(self, url: str) -> dict:
        """
        Estimate pages from homepage link density.

        This is a conservative estimate.
        """
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract all internal links
            base_domain = urlparse(url).netloc
            internal_links = set()

            for a in soup.find_all("a", href=True):
                href = a["href"]

                # Parse the href
                try:
                    href_parsed = urlparse(href)

                    # Check if it's an internal link
                    if href_parsed.netloc == "" or href_parsed.netloc == base_domain:
                        # Ignore common non-content links
                        if not self._is_excluded_path(href_parsed.path):
                            # Normalize and add
                            full_url = urljoin(url, href)
                            internal_links.add(full_url)

                except Exception:
                    continue

            # Conservative estimate: assume 1 internal link = ~5 pages
            # Sites typically have more pages than homepage links
            link_count = len(internal_links)

            # Cap at reasonable maximum
            estimated = max(1, min(500, link_count * 5))

            return {
                "page_count": estimated,
                "confidence": 0.6,
                "source": "homepage",
                "internal_links_found": link_count
            }

        except Exception as e:
            return {"page_count": 1, "confidence": 0.3, "source": "homepage", "error": str(e)}

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from page count."""
        excluded_patterns = [
            r"^/wp-admin",
            r"^/admin",
            r"^/api",
            r"^/login",
            r"^/logout",
            r"^/register",
            r"^/cart",
            r"^/checkout",
            r"^/account",
            r"^/user",
            r"^/search",
            r"^/feed",
            r"^/rss",
            r"^/track",
            r"^/comment",
            r"^/email",
            r"^/share",
            r"^/javascript:",
            r"^mailto:",
            r"^tel:",
        ]

        path_lower = path.lower()

        for pattern in excluded_patterns:
            if re.match(pattern, path_lower):
                return True

        return False

    async def discover_urls(self, url: str, sitemap_url: Optional[str] = None) -> dict:
        """
        Discover all URLs for a site.

        Args:
            url: The base URL to scan
            sitemap_url: Optional manual sitemap URL (if auto-discovery fails)

        Returns:
            {
                "urls": list[str],  # List of discovered URLs
                "source": str,      # "sitemap", "homepage", "manual_sitemap"
                "confidence": float,
                "sitemap_found": bool,
                "sitemap_url": Optional[str],
                "error": Optional[str]
            }
        """
        try:
            # Security: Validate URL to prevent SSRF attacks
            is_valid, error_msg = validate_url_safe(url)
            if not is_valid:
                return {
                    "urls": [],
                    "source": "error",
                    "confidence": 0.0,
                    "sitemap_found": False,
                    "sitemap_url": None,
                    "error": f"URL validation failed: {error_msg}"
                }

            # Normalize URL
            url = normalize_url(url)
            parsed = urlparse(url)

            # If manual sitemap URL provided, use it directly
            if sitemap_url:
                is_valid_sitemap, sitemap_error = validate_url_safe(sitemap_url)
                if not is_valid_sitemap:
                    return {
                        "urls": [],
                        "source": "manual_sitemap",
                        "confidence": 0.0,
                        "sitemap_found": False,
                        "sitemap_url": None,
                        "error": f"Invalid sitemap URL: {sitemap_error}"
                    }

                urls = await self._get_urls_from_sitemap(sitemap_url)
                if urls:
                    return {
                        "urls": urls,
                        "source": "manual_sitemap",
                        "confidence": 1.0,
                        "sitemap_found": True,
                        "sitemap_url": sitemap_url
                    }
                else:
                    return {
                        "urls": [],
                        "source": "manual_sitemap",
                        "confidence": 0.0,
                        "sitemap_found": True,
                        "sitemap_url": sitemap_url,
                        "error": "Could not extract URLs from provided sitemap"
                    }

            # Try auto-discovery from robots.txt or common locations
            auto_sitemap_url = await self._find_sitemap(url)
            if auto_sitemap_url:
                urls = await self._get_urls_from_sitemap(auto_sitemap_url)
                if urls:
                    return {
                        "urls": urls,
                        "source": "sitemap",
                        "confidence": 1.0,
                        "sitemap_found": True,
                        "sitemap_url": auto_sitemap_url
                    }

            # Fallback: get URLs from homepage
            urls = await self._get_internal_links(url)
            return {
                "urls": urls,
                "source": "homepage",
                "confidence": 0.6,
                "sitemap_found": False,
                "sitemap_url": None,
                "warning": "No sitemap found. Discovered URLs from homepage links. "
                           "Consider providing a sitemap URL manually for more accurate results."
            }

        except Exception as e:
            return {
                "urls": [],
                "source": "error",
                "confidence": 0.0,
                "sitemap_found": False,
                "sitemap_url": None,
                "error": str(e)
            }

    async def _get_urls_from_sitemap(self, sitemap_url: str) -> list:
        """Extract all URLs from a sitemap (handles sitemap indexes)."""
        client = await self._get_client()

        try:
            # Security: Check content-length first to prevent DoS
            head_response = await client.head(sitemap_url)
            content_length = int(head_response.headers.get("content-length", 0))
            if content_length > MAX_CONTENT_SIZE:
                # Return empty if too large
                return []

            response = await client.get(sitemap_url)
            response.raise_for_status()

            # Security: Limit response size
            if len(response.content) > MAX_CONTENT_SIZE:
                return []

            # Check if it's a sitemap index
            if "<sitemapindex" in response.text.lower():
                return await self._get_urls_from_sitemap_index(sitemap_url, response.text)

            # Regular sitemap - extract URLs
            return self._extract_urls_from_xml(response.text)

        except Exception:
            return []

    async def _get_urls_from_sitemap_index(self, sitemap_url: str, index_text: str) -> list:
        """Extract URLs from a sitemap index (references other sitemaps)."""
        soup = BeautifulSoup(index_text, "xml")

        # Find all sitemap locations
        sitemap_locs = [loc.text for loc in soup.find_all("loc") if "sitemap" in loc.parent.name.lower()]

        if not sitemap_locs:
            return []

        # Security: Limit sub-sitemaps to prevent DoS
        all_urls = []
        tasks = []

        for loc in sitemap_locs[:10]:  # Limit for performance
            tasks.append(self._get_urls_from_sitemap(loc))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_urls.extend(result)

        # Security: Cap at maximum
        return all_urls[:MAX_SITEMAP_URLS]

    async def _get_internal_links(self, url: str) -> list:
        """Extract internal links from homepage."""
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract all internal links
            base_domain = urlparse(url).netloc
            internal_links = set()

            for a in soup.find_all("a", href=True):
                href = a["href"]

                # Parse the href
                try:
                    href_parsed = urlparse(href)

                    # Check if it's an internal link
                    if href_parsed.netloc == "" or href_parsed.netloc == base_domain:
                        # Ignore common non-content links
                        if not self._is_excluded_path(href_parsed.path):
                            # Normalize and add
                            full_url = urljoin(url, href)
                            internal_links.add(full_url)

                except Exception:
                    continue

            # Return as list, capped at reasonable maximum
            return list(internal_links)[:500]

        except Exception:
            return []


async def discover_site_urls(url: str, sitemap_url: Optional[str] = None) -> dict:
    """
    Convenience function to discover URLs for a site.

    Args:
        url: The base URL to scan
        sitemap_url: Optional manual sitemap URL (if auto-discovery fails)

    Returns:
        Dict with urls, source, confidence, sitemap_found, sitemap_url, error
    """
    scanner = SiteScanner()
    try:
        return await scanner.discover_urls(url, sitemap_url)
    finally:
        await scanner.close()


async def quick_page_count(url: str) -> int:
    """
    Quick function to get page count for a URL.
    Convenience function for use in other modules.
    """
    scanner = SiteScanner()
    try:
        result = await scanner.estimate_pages(url)
        return result.get("page_count", 1)
    finally:
        await scanner.close()
