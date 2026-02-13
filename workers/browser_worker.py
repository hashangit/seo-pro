"""
Browser Worker - Visual & Performance Analysis

Executes Playwright-based analyses (visual, performance, images).
Deployed on Cloud Run with scale-to-zero.

Features:
- Multi-viewport screenshots
- Above-the-fold analysis
- Core Web Vitals (LCP, INP, CLS)
- Image optimization analysis
- Mobile viewport testing
"""

import asyncio
import os
from typing import Any, Dict, List
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import URL validator for SSRF protection
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api.utils.url_validator import validate_url_safe, is_valid_url_format

# Task status update function
async def update_task_status(task_id: str, audit_id: str, status: str, results: Any = None):
    """Update task status in Supabase with retry logic."""
    import httpx
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


def round(value: float, digits: int = 0) -> float:
    """Round helper function (missing import in original code)."""
    multiplier = 10 ** digits
    return int(value * multiplier) / multiplier

app = FastAPI(title="SEO Pro Browser Worker")


class AnalyzeRequest(BaseModel):
    """Request model for page analysis."""
    url: str
    viewport_width: int = 1920
    viewport_height: int = 1080
    screenshots: bool = True
    performance: bool = True


async def capture_screenshot(url: str, width: int, height: int) -> bytes:
    """Capture screenshot using Playwright with proper cleanup on error."""
    from playwright.async_api import async_playwright
    import base64

    browser = None
    try:
        async with async_playwright() as p:
            # Cloud Run compatibility flags for Playwright
            browser = await p.chromium.launch(
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--no-sandbox",
                    "--disable-gpu",
                ]
            )
            page = await browser.new_page(
                viewport={"width": width, "height": height}
            )

            await page.goto(url, wait_until="networkidle", timeout=30000)
            screenshot = await page.screenshot(full_page=False)

            return screenshot
    finally:
        # CRITICAL: Always close browser even on error
        if browser is not None:
            await browser.close()


async def analyze_visuals(url: str) -> Dict[str, Any]:
    """Visual analysis with screenshots and proper cleanup."""
    from playwright.async_api import async_playwright
    import base64

    results = {
        "category": "visual",
        "url": url,
        "viewports": [],
        "above_the_fold": {},
        "issues": [],
    }

    viewports = [
        {"name": "desktop", "width": 1920, "height": 1080},
        {"name": "tablet", "width": 768, "height": 1024},
        {"name": "mobile", "width": 375, "height": 812},
    ]

    browser = None
    try:
        async with async_playwright() as p:
            # Cloud Run compatibility flags for Playwright
            browser = await p.chromium.launch(
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--no-sandbox",
                    "--disable-gpu",
                ]
            )

            for vp in viewports:
                page = await browser.new_page(
                    viewport={"width": vp["width"], "height": vp["height"]}
                )

                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Capture screenshot
                screenshot = await page.screenshot(full_page=False)

                # Check above-the-fold elements
                h1_visible = await page.locator("h1").is_visible()
                cta_visible = await page.locator("button, a[href*=contact], a[href*=signup]").is_visible()

                # FIX: Use proper base64 encoding
                b64_encoded = base64.b64encode(screenshot).decode()
                results["viewports"].append({
                    "name": vp["name"],
                    "width": vp["width"],
                    "height": vp["height"],
                    "screenshot_b64": b64_encoded[:1000] + "...",  # Truncated for JSON
                })

                results["above_the_fold"][vp["name"]] = {
                    "h1_visible": h1_visible,
                    "cta_visible": cta_visible,
                }

                await page.close()

            return results
    finally:
        # CRITICAL: Always close browser even on error
        if browser is not None:
            await browser.close()


async def analyze_performance(url: str) -> Dict[str, Any]:
    """Core Web Vitals analysis with proper cleanup."""
    from playwright.async_api import async_playwright

    results = {
        "category": "performance",
        "url": url,
        "metrics": {},
        "issues": [],
        "passes": [],
    }

    browser = None
    try:
        async with async_playwright() as p:
            # Cloud Run compatibility flags for Playwright
            browser = await p.chromium.launch(
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--no-sandbox",
                    "--disable-gpu",
                ]
            )
            page = await browser.new_page()

            # Enable performance monitoring
            metrics = await page.evaluate("""
                () => {
                    return new Promise(resolve => {
                        if (window.PerformanceObserver) {
                            const observer = new PerformanceObserver(list => {
                                const entries = list.getEntries();
                                resolve(entries);
                            });
                        observer.observe({entryTypes: ['largest-contentful-paint', 'layout-shift']});
                        setTimeout(() => resolve([]), 5000);
                    } else {
                        resolve([]);
                    }
                });
            }
            """)

            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Get basic timing metrics
            nav_timing = await page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                        loadComplete: timing.loadEventEnd - timing.navigationStart,
                        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || null
                    };
                }
            """)

            results["metrics"] = {
                "dom_content_loaded_ms": round(nav_timing.get("domContentLoaded", 0), 2),
                "load_complete_ms": round(nav_timing.get("loadComplete", 0), 2),
                "first_paint_ms": round(nav_timing.get("firstPaint", 0), 2),
            }

            # Assess Core Web Vitals thresholds
            lcp_threshold = 2500  # 2.5s
            if nav_timing.get("loadComplete", 9999) <= lcp_threshold:
                results["passes"].append({
                    "check": "LCP (proxy)",
                    "status": "pass",
                    "value": f"{nav_timing.get('loadComplete')}ms"
                })
            else:
                results["issues"].append({
                    "check": "LCP (proxy)",
                    "status": "fail",
                    "value": f"{nav_timing.get('loadComplete')}ms (target: <{lcp_threshold}ms)"
                })

            return results
    finally:
        # CRITICAL: Always close browser even on error
        if browser is not None:
            await browser.close()


async def analyze_images(url: str) -> Dict[str, Any]:
    """Image optimization analysis with proper cleanup."""
    from playwright.async_api import async_playwright

    results = {
        "category": "images",
        "url": url,
        "total_images": 0,
        "issues": [],
        "warnings": [],
        "passes": [],
    }

    browser = None
    try:
        async with async_playwright() as p:
            # Cloud Run compatibility flags for Playwright
            browser = await p.chromium.launch(
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--no-sandbox",
                    "--disable-gpu",
                ]
            )
            page = await browser.new_page()

            await page.goto(url, wait_until="networkidle", timeout=30000)

            images = await page.locator("img").all()

            results["total_images"] = len(images)

            for img in images:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                width = await img.get_attribute("width")
                height = await img.get_attribute("height")

                if not alt:
                    results["issues"].append({
                        "check": "Alt text",
                        "status": "fail",
                        "value": src[:100] if src else "no-src"
                    })

                if not width or not height:
                    results["warnings"].append({
                        "check": "Image dimensions",
                        "status": "warning",
                        "value": src[:100] if src else "no-src"
                    })

            return results
    finally:
        # CRITICAL: Always close browser even on error
        if browser is not None:
            await browser.close()


async def analyze_page(task: Dict[str, Any]) -> Dict[str, Any]:
    """Run all Playwright-based analyses on a page with proper error handling."""
    url = task.get("url")

    if not url:
        raise HTTPException(status_code=400, detail="URL required")

    # SECURITY: Validate URL to prevent SSRF attacks
    if not is_valid_url_format(url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    if not validate_url_safe(url):
        raise HTTPException(status_code=400, detail="URL not allowed (SSRF protection)")

    # Run analyses
    results = {
        "url": url,
        "analyses": []
    }

    try:
        visual = await analyze_visuals(url)
        results["analyses"].append(visual)
    except Exception as e:
        results["analyses"].append({
            "category": "visual",
            "error": str(e)
        })

    try:
        performance = await analyze_performance(url)
        results["analyses"].append(performance)
    except Exception as e:
        results["analyses"].append({
            "category": "performance",
            "error": str(e)
        })

    try:
        images = await analyze_images(url)
        results["analyses"].append(images)
    except Exception as e:
        results["analyses"].append({
            "category": "images",
            "error": str(e)
        })

    return results


# Endpoints
@app.get("/health")
async def health():
    """Health check for Cloud Run."""
    return {"status": "healthy", "worker": "browser"}


@app.post("/analyze")
async def analyze(task: AnalyzeRequest):
    """Analyze a page with Playwright and update task status."""
    task_data = task.dict()
    result = await analyze_page(task_data)

    # Update task status in Supabase
    await update_task_status(
        task_id=task_data.get("task_id"),
        audit_id=task_data.get("audit_id"),
        status="completed",
        results=result
    )

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
