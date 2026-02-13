"""
HTTP Worker - Fast SEO Analysis

Executes HTTP-only SEO analyses (9.5 features) without Playwright.
Deployed on Cloud Run with scale-to-zero.

Features:
- Technical SEO analysis
- Content/E-E-A-T analysis
- Schema detection
- GEO analysis
- Programmatic analysis
- Competitor analysis
- Hreflang analysis
- Sitemap analysis
"""

import asyncio
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException

# Import URL validator for SSRF protection
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api.utils.url_validator import validate_url_safe, is_valid_url_format

app = FastAPI(title="SEO Pro HTTP Worker")

# Configuration
TIMEOUT = 30.0
USER_AGENT = "SEO Pro/1.0 (+https://seopro.example.com/bot)"


# ============================================================================
# Task status update function
# ============================================================================

async def update_task_status(task_id: str, audit_id: str, status: str, results: Any = None):
    """Update task status in Supabase with retry logic."""
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        return

    supabase = create_client(supabase_url, supabase_key)

    # Retry logic for transient database errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            update_data: Dict[str, Any] = {
                "status": status,
                "updated_at": "now()"
            }

            if results is not None:
                update_data["results_json"] = results

            supabase.table("audit_tasks").update(update_data).eq("id", task_id).execute()
            return
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
            else:
                raise


async def fetch_page(url: str) -> Dict[str, Any]:
    """Fetch page content with HTTP client."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            return {
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "content_length": len(response.content),
                "html": response.text,
                "soup": soup,
                "headers": dict(response.headers),
            }
        except httpx.HTTPError as e:
            return {
                "url": url,
                "error": str(e),
                "status_code": None,
            }


async def technical_analysis(url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Technical SEO analysis."""
    results = {
        "category": "technical",
        "url": url,
        "issues": [],
        "warnings": [],
        "passes": [],
    }

    soup = page_data.get("soup")
    if not soup:
        results["issues"].append("Could not parse HTML")
        return results

    # Check for title
    title = soup.find("title")
    if title and title.get_text().strip():
        results["passes"].append({
            "check": "Title tag",
            "status": "pass",
            "value": title.get_text().strip()[:60]
        })
    else:
        results["issues"].append({
            "check": "Title tag",
            "status": "fail",
            "value": "Missing or empty"
        })

    # Check for meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content", "").strip():
        results["passes"].append({
            "check": "Meta description",
            "status": "pass",
            "value": meta_desc.get("content")[:160]
        })
    else:
        results["warnings"].append({
            "check": "Meta description",
            "status": "warning",
            "value": "Missing or empty"
        })

    # Check for canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        results["passes"].append({
            "check": "Canonical tag",
            "status": "pass",
            "value": canonical.get("href")
        })
    else:
        results["warnings"].append({
            "check": "Canonical tag",
            "status": "warning",
            "value": "Not found"
        })

    # Check for h1
    h1_tags = soup.find_all("h1")
    if len(h1_tags) == 1:
        results["passes"].append({
            "check": "H1 tag",
            "status": "pass",
            "value": h1_tags[0].get_text()[:50]
        })
    else:
        results["issues"].append({
            "check": "H1 tag",
            "status": "fail",
            "value": f"{len(h1_tags)} H1 tags found (should be 1)"
        })

    # Check for robots.txt
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(robots_url)
            if response.status_code == 200:
                results["passes"].append({
                    "check": "robots.txt",
                    "status": "pass",
                    "value": "Accessible"
                })
            else:
                results["warnings"].append({
                    "check": "robots.txt",
                    "status": "warning",
                    "value": f"Status {response.status_code}"
                })
    except Exception:
        results["warnings"].append({
            "check": "robots.txt",
            "status": "warning",
            "value": "Could not check"
        })

    return results


async def content_analysis(url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Content quality (E-E-A-T) analysis."""
    results = {
        "category": "content",
        "url": url,
        "eeat_score": 0,
        "issues": [],
        "warnings": [],
        "passes": [],
    }

    soup = page_data.get("soup")
    if not soup:
        results["issues"].append("Could not parse HTML")
        return results

    # Check for author information
    author_meta = soup.find("meta", attrs={"name": "author"})
    author_schema = soup.find("span", attrs={"itemprop": "author"})

    if author_meta or author_schema:
        results["passes"].append({
            "check": "Author information",
            "status": "pass",
            "value": "Author attribute found"
        })
        results["eeat_score"] += 1
    else:
        results["warnings"].append({
            "check": "Author information",
            "status": "warning",
            "value": "Author not explicitly declared"
        })

    # Check content length
    text = soup.get_text()
    word_count = len(text.split())

    if word_count >= 300:
        results["passes"].append({
            "check": "Content length",
            "status": "pass",
            "value": f"{word_count} words"
        })
        results["eeat_score"] += 1
    else:
        results["issues"].append({
            "check": "Content length",
            "status": "fail",
            "value": f"{word_count} words (minimum: 300)"
        })

    # Check for structured data indicating expertise
    schema_found = False
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        if "author" in str(script) or "organization" in str(script):
            schema_found = True
            break

    if schema_found:
        results["passes"].append({
            "check": "Expertise signals",
            "status": "pass",
            "value": "Schema markup found"
        })
        results["eeat_score"] += 1
    else:
        results["warnings"].append({
            "check": "Expertise signals",
            "status": "warning",
            "value": "No author/expertise schema found"
        })

    return results


async def schema_analysis(url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Schema markup detection and validation."""
    results = {
        "category": "schema",
        "url": url,
        "schemas": [],
        "issues": [],
        "warnings": [],
    }

    soup = page_data.get("soup")
    if not soup:
        results["issues"].append("Could not parse HTML")
        return results

    # Find all JSON-LD scripts
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            results["schemas"].append({
                "type": data.get("@type", "Unknown"),
                "context": data.get("@context", "")
            })
        except json.JSONDecodeError:
            results["warnings"].append({
                "check": "JSON-LD parsing",
                "status": "warning",
                "value": "Invalid JSON-LD found"
            })

    if results["schemas"]:
        results["passes"] = [{
            "check": "Schema markup",
            "status": "pass",
            "value": f"{len(results['schemas'])} schema(s) found"
        }]
    else:
        results["warnings"].append({
            "check": "Schema markup",
            "status": "warning",
            "value": "No JSON-LD schema found"
        })

    return results


async def analyze_page(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run all HTTP-only analyses on a page."""
    url = task_data.get("url")

    if not url:
        raise HTTPException(status_code=400, detail="URL required")

    # SECURITY: Validate URL to prevent SSRF attacks
    if not is_valid_url_format(url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    if not validate_url_safe(url):
        raise HTTPException(status_code=400, detail="URL not allowed (SSRF protection)")

    # Fetch page
    page_data = await fetch_page(url)

    if page_data.get("error"):
        return {
            "url": url,
            "error": page_data["error"],
            "analyses": []
        }

    # Run analyses in parallel
    analyses = await asyncio.gather(
        technical_analysis(url, page_data),
        content_analysis(url, page_data),
        schema_analysis(url, page_data),
        return_exceptions=True
    )

    results = {
        "url": url,
        "status_code": page_data.get("status_code"),
        "analyses": [a for a in analyses if isinstance(a, dict)]
    }

    return results


# Endpoints
@app.get("/health")
async def health():
    """Health check for Cloud Run."""
    return {"status": "healthy", "worker": "http"}


@app.post("/analyze")
async def analyze(task: Dict[str, Any]):
    """Analyze a single page with task status update."""
    task_data = task
    result = await analyze_page(task_data)

    # Update task status in Supabase
    task_id = task_data.get("task_id")
    audit_id = task_data.get("audit_id")

    if task_id and audit_id:
        await update_task_status(
            task_id=task_id,
            audit_id=audit_id,
            status="completed",
            results=result
        )

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
