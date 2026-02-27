"""
SDK Worker - Unified SEO Analysis with Claude Agent SDK

This worker replaces both HTTP Worker and Browser Worker.
It loads Skills and Agents from the filesystem (same as Claude Code CLI)
and uses Claude Agent SDK for multi-agent orchestration.

Features:
- Loads skills/ and agents/ from filesystem (same files as CLI)
- Uses Claude Agent SDK for agent orchestration
- Runs scripts/*.py via Bash tool
- Uses Playwright via Bash for browser automation
- Single unified service for all analysis types

Deployed on Cloud Run with scale-to-zero.
"""

import asyncio
import os

# Import shared utilities
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.utils.url_validator import is_valid_url_format, validate_url_safe

app = FastAPI(title="SEO Pro SDK Worker")


# ============================================================================
# Request/Response Models
# ============================================================================


class AnalyzeRequest(BaseModel):
    """Request model for SEO analysis."""

    url: str
    task_id: str | None = None
    audit_id: str | None = None
    analysis_type: str = "full"  # full, technical, content, schema, visual, performance, etc.
    prompt: str | None = None  # Custom prompt override


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    worker: str
    version: str


# ============================================================================
# Task Status Update
# ============================================================================


async def update_task_status(task_id: str, audit_id: str, status: str, results: Any = None):
    """Update task status in Supabase with retry logic."""
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        print("Warning: Supabase credentials not configured")
        return

    supabase = create_client(supabase_url, supabase_key)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # updated_at is handled automatically by DB trigger
            update_data: dict[str, Any] = {"status": status}

            if results is not None:
                update_data["result_json"] = results

            # Set completed_at for terminal states
            if status in ("completed", "failed"):
                from datetime import datetime
                update_data["completed_at"] = datetime.utcnow().isoformat()

            supabase.table("audit_tasks").update(update_data).eq("id", task_id).execute()
            return
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2**attempt))
            else:
                print(f"Failed to update task status: {e}")


# ============================================================================
# Claude Agent SDK Integration
# ============================================================================


async def run_seo_analysis_with_sdk(
    url: str, analysis_type: str = "full", custom_prompt: str | None = None
) -> dict[str, Any]:
    """
    Run SEO analysis using Claude Agent SDK.

    The SDK loads Skills and Agents from the filesystem:
    - .claude/skills/seo-audit/SKILL.md
    - .claude/agents/seo-technical.md
    - .claude/agents/seo-content.md
    - etc.

    This is the same architecture as Claude Code CLI!
    """
    from claude_agent_sdk import ClaudeAgentOptions, query

    # Determine the prompt based on analysis type
    if custom_prompt:
        prompt = custom_prompt
    elif analysis_type == "full":
        prompt = f"Run a full SEO audit on {url}"
    else:
        prompt = f"Run {analysis_type} SEO analysis on {url}"

    # Project root contains skills/ and agents/
    project_root = os.getenv("PROJECT_ROOT", "/app")

    results = []
    final_result = None

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                # Point to project root with skills/ and agents/
                cwd=project_root,
                # Load Skills and Agents from filesystem
                setting_sources=["project"],
                # Tools the agent can use
                # - Skill: To invoke seo-audit skill
                # - Task: For subagent delegation (seo-technical, seo-content, etc.)
                # - Bash: To run scripts/fetch_page.py, playwright commands
                # - Read/Write/Glob/Grep: File operations
                allowed_tools=[
                    "Skill",
                    "Task",
                    "Bash",
                    "Read",
                    "Write",
                    "Glob",
                    "Grep",
                    "WebFetch",
                    "mcp__plugin_playwright_playwright__browser_navigate",
                    "mcp__plugin_playwright_playwright__browser_snapshot",
                    "mcp__plugin_playwright_playwright__browser_take_screenshot",
                    "mcp__plugin_playwright_playwright__browser_console_messages",
                    "mcp__plugin_playwright_playwright__browser_network_requests",
                    "mcp__plugin_playwright_playwright__browser_evaluate",
                ],
                # Run without permission prompts (production mode)
                permission_mode="bypassPermissions",
                # Model selection (use Sonnet for cost-efficiency)
                model="claude-sonnet-4-5-20250219",
            ),
        ):
            # Collect messages for streaming/progress
            if hasattr(message, "content") and message.content:
                results.append(message.content)

            # Capture final result
            if hasattr(message, "result") and message.result:
                final_result = message.result

        # Return structured result
        if final_result:
            return {
                "url": url,
                "analysis_type": analysis_type,
                "status": "completed",
                "result": final_result,
                "messages": results,
            }
        else:
            # Fallback: combine all messages
            return {
                "url": url,
                "analysis_type": analysis_type,
                "status": "completed",
                "result": "\n".join(str(r) for r in results if r),
                "messages": results,
            }

    except Exception as e:
        return {"url": url, "analysis_type": analysis_type, "status": "error", "error": str(e)}


# ============================================================================
# Fallback: Direct Analysis (when SDK not available)
# ============================================================================


async def run_seo_analysis_fallback(url: str, analysis_type: str = "full") -> dict[str, Any]:
    """
    Fallback analysis using direct API calls when Claude Agent SDK is unavailable.

    This provides basic analysis capability without the full SDK orchestration.
    """
    import httpx
    from bs4 import BeautifulSoup

    results = {"url": url, "analysis_type": analysis_type, "status": "completed", "analyses": []}

    # Fetch page
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "SEO Pro/1.0 (+https://seopro.example.com/bot)"},
                follow_redirects=True,
            )
            response.raise_for_status()

            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # Basic technical analysis
            if analysis_type in ["full", "technical"]:
                title = soup.find("title")
                meta_desc = soup.find("meta", attrs={"name": "description"})
                h1s = soup.find_all("h1")
                canonical = soup.find("link", rel="canonical")

                results["analyses"].append(
                    {
                        "category": "technical",
                        "score": 70,
                        "issues": [] if title else ["Missing title tag"],
                        "warnings": [] if meta_desc else ["Missing meta description"],
                        "passes": [f"Title: {title.text[:50]}..."] if title else [],
                        "recommendations": [
                            "Add meta description" if not meta_desc else None,
                            "Add canonical URL" if not canonical else None,
                        ],
                    }
                )

            # Basic content analysis
            if analysis_type in ["full", "content"]:
                text_content = soup.get_text()
                word_count = len(text_content.split())

                results["analyses"].append(
                    {
                        "category": "content",
                        "score": 60 if word_count > 300 else 40,
                        "issues": [] if word_count > 300 else ["Thin content"],
                        "warnings": [],
                        "passes": [f"Word count: {word_count}"],
                        "recommendations": ["Increase content depth" if word_count < 300 else None],
                    }
                )

            # Basic schema analysis
            if analysis_type in ["full", "schema"]:
                json_ld = soup.find_all("script", type="application/ld+json")
                results["analyses"].append(
                    {
                        "category": "schema",
                        "score": 50 if json_ld else 0,
                        "issues": [] if json_ld else ["No structured data found"],
                        "warnings": [],
                        "passes": [f"Found {len(json_ld)} JSON-LD blocks"] if json_ld else [],
                        "recommendations": ["Add JSON-LD structured data"],
                    }
                )

    except httpx.HTTPError as e:
        results["error"] = str(e)
        results["status"] = "error"

    return results


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check for Cloud Run."""
    # Check if SDK is available
    sdk_available = True
    try:
        from claude_agent_sdk import query  # noqa: F401
    except ImportError:
        sdk_available = False

    return HealthResponse(
        status="healthy" if sdk_available else "degraded", worker="sdk", version="3.0.0"
    )


@app.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Analyze a page using Claude Agent SDK with filesystem Skills.

    This endpoint loads skills/ and agents/ from the filesystem,
    providing the same multi-agent orchestration as Claude Code CLI.
    """
    # Validate URL
    if not is_valid_url_format(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    if not validate_url_safe(request.url):
        raise HTTPException(status_code=400, detail="URL not allowed (SSRF protection)")

    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")
    is_production = environment == "production"

    # Try SDK first
    try:
        from claude_agent_sdk import query  # noqa: F401

        result = await run_seo_analysis_with_sdk(
            url=request.url, analysis_type=request.analysis_type, custom_prompt=request.prompt
        )
    except ImportError:
        # P0 FIX: In production, fail fast instead of using inferior fallback
        # Users are charged full credits and should get full quality analysis
        if is_production:
            print("CRITICAL: Claude Agent SDK not available in production!")
            raise HTTPException(
                status_code=503, detail="Analysis service unavailable. Please try again later."
            )

        # Only use fallback in development
        print("Warning: Claude Agent SDK not available, using fallback (development only)")
        result = await run_seo_analysis_fallback(
            url=request.url, analysis_type=request.analysis_type
        )

    # Update task status if task_id provided
    if request.task_id and request.audit_id:
        status = "completed" if result.get("status") != "error" else "failed"
        await update_task_status(
            task_id=request.task_id, audit_id=request.audit_id, status=status, results=result
        )

    return result


@app.post("/analyze/page")
async def analyze_page(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Deep single-page SEO analysis.

    Comprehensive analysis of a single page covering:
    - On-page SEO (title, meta, headings, URL structure)
    - Content quality (word count, readability, E-E-A-T signals)
    - Technical elements (canonical, robots, OG tags, hreflang)
    - Schema markup detection and validation
    - Image optimization
    - Core Web Vitals indicators
    """
    request.analysis_type = "page"
    return await analyze(request)


@app.post("/analyze/technical")
async def analyze_technical(request: AnalyzeRequest) -> dict[str, Any]:
    """Run technical SEO analysis only."""
    request.analysis_type = "technical"
    return await analyze(request)


@app.post("/analyze/content")
async def analyze_content(request: AnalyzeRequest) -> dict[str, Any]:
    """Run content quality analysis only."""
    request.analysis_type = "content"
    return await analyze(request)


@app.post("/analyze/schema")
async def analyze_schema(request: AnalyzeRequest) -> dict[str, Any]:
    """Run schema markup analysis only."""
    request.analysis_type = "schema"
    return await analyze(request)


@app.post("/analyze/visual")
async def analyze_visual(request: AnalyzeRequest) -> dict[str, Any]:
    """Run visual SEO analysis only."""
    request.analysis_type = "visual"
    return await analyze(request)


@app.post("/analyze/performance")
async def analyze_performance(request: AnalyzeRequest) -> dict[str, Any]:
    """Run performance/Core Web Vitals analysis only."""
    request.analysis_type = "performance"
    return await analyze(request)


@app.post("/analyze/geo")
async def analyze_geo(request: AnalyzeRequest) -> dict[str, Any]:
    """Run GEO (AI Search optimization) analysis only."""
    request.analysis_type = "geo"
    return await analyze(request)


@app.post("/analyze/sitemap")
async def analyze_sitemap(request: AnalyzeRequest) -> dict[str, Any]:
    """Run sitemap analysis only."""
    request.analysis_type = "sitemap"
    return await analyze(request)


@app.post("/analyze/hreflang")
async def analyze_hreflang(request: AnalyzeRequest) -> dict[str, Any]:
    """Run hreflang/international SEO analysis only."""
    request.analysis_type = "hreflang"
    return await analyze(request)


@app.post("/analyze/images")
async def analyze_images(request: AnalyzeRequest) -> dict[str, Any]:
    """Run image SEO analysis only."""
    request.analysis_type = "images"
    return await analyze(request)


@app.post("/analyze/plan")
async def analyze_plan(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Run strategic SEO planning analysis.

    Creates industry-specific SEO strategy with templates for:
    - SaaS, E-commerce, Local Service, Publisher, Agency
    """
    request.analysis_type = "plan"
    return await analyze(request)


@app.post("/analyze/programmatic")
async def analyze_programmatic(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Run programmatic SEO analysis and planning.

    Analyzes scale SEO opportunities and creates implementation plans.
    """
    request.analysis_type = "programmatic"
    return await analyze(request)


@app.post("/analyze/competitor-pages")
async def analyze_competitor_pages(request: AnalyzeRequest) -> dict[str, Any]:
    """
    Analyze competitor comparison pages for SEO, GEO, and AEO.

    Analyzes existing "X vs Y" and "Alternatives to X" pages on your site for:
    - SEO optimization (title, meta, headings, schema)
    - GEO (Generative Engine Optimization) for AI search
    - AEO (Answer Engine Optimization) for voice/answer engines
    - Content quality and E-E-A-T signals
    """
    request.analysis_type = "competitor-pages"
    return await analyze(request)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
