# SEO Pro Features

Comprehensive SEO analysis and optimization capabilities for Claude Code.

## 1. Full Website Audit (`/seo audit`)
Parallel, automated analysis across your entire site (up to 500 pages).
- **Parallel Subagents**: Uses 6 specialized subagents (Technical, Content, Schema, Sitemap, Performance, Visual) to analyze in parallel.
- **Business Type Detection**: Automatically detects business type (SaaS, Ecommerce, Local, etc.) to tailor analysis.
- **SEO Health Score**: Calculates an overall score (0-100) based on weighted categories.
- **Prioritized Action Plan**: Generates an `ACTION-PLAN.md` with tasks ranked by priority (Critical → Low).
- **Comprehensive Reporting**: Delivers a detailed `FULL-AUDIT-REPORT.md`.

## 2. Technical SEO (`/seo technical`)
Deep inspection of the technical foundation of your website.
- **Crawlability & Indexability**: robots.txt, sitemaps, canonicals, noindex tags, and redirect chains.
- **Core Web Vitals**: Analyzes LCP, INP (Interactivity), and CLS. (Fully updated: INP replaces FID).
- **Security**: HTTPS validation and security header analysis.
- **URL Structure**: Clean URLs, depth analysis, and path optimization.
- **Mobile Optimization**: Viewport settings, touch target sizing, and mobile-first readiness.
- **JavaScript Rendering**: Detects Client-Side Rendering (CSR) vs. Server-Side Rendering (SSR) issues.

## 3. Content Quality & E-E-A-T (`/seo content`)
Evaluates content based on Google's September 2025 Quality Rater Guidelines.
- **E-E-A-T Scoring**: Experience, Expertise, Authoritativeness, and Trustworthiness assessment.
- **AI Citation Readiness**: Scores content on how likely it is to be cited by AI search engines.
- **Readability Analysis**: Word count thresholds per page type and readability metrics.
- **Content Freshness**: Detects update signals and "fake freshness" patterns.
- **AI Content Assessment**: Flags low-quality AI-generated content markers.

## 4. AI Search & GEO Optimization (`/seo geo`)
Generative Engine Optimization (GEO) for the AI-first search era.
- **Citability Scoring**: Identifies and optimizes "answer blocks" (134-167 words) for AI citations.
- **Structural Readability**: Optimization for headings, lists, and tables to aid AI parsing.
- **AI Crawler Management**: Detection and configuration for GPTBot, ClaudeBot, PerplexityBot, etc.
- **llms.txt Support**: Validates and recommends `/llms.txt` implementation.
- **Brand Mention Analysis**: Analyzes presence across YouTube, Reddit, and Wikipedia.

## 5. Schema & Structured Data (`/seo schema`)
Maximizes rich result opportunities and entity clarity.
- **Multi-Format Detection**: Identifies JSON-LD, Microdata, and RDFa.
- **Validation**: Checks against Google's latest requirements and deprecation notices (e.g., FAQ/HowTo changes).
- **Opportunity Detection**: Suggests missing schema types based on content.
- **Code Generation**: Generates ready-to-use JSON-LD snippets.

## 6. Programmatic SEO (`/seo programmatic`)
Safeguards and strategies for building SEO pages at scale.
- **Data Source Quality**: Evaluates the uniqueness and quality of data used for scaling.
- **Thin Content Safeguards**: Quality gates to prevent "doorway page" penalties.
- **Index Bloat Prevention**: Strategies for pagination, faceted navigation, and low-value pages.
- **Internal Linking Automation**: Hub/spoke and breadcrumb strategy planning.

## 7. Competitor Comparison (`/seo competitor-pages`)
Tools for creating high-converting comparison and alternatives pages.
- **Layout Generation**: Creates "X vs Y" and "Alternatives to X" page structures.
- **Feature Matrices**: Builds comparison tables with scoring.
- **Product Schema**: Includes AggregateRating and Offer markup for comparison pages.
- **Fairness Guidelines**: Ensures accurate competitor representation and source citations.

## 8. International SEO (`/seo hreflang`)
Global reach validation and generation.
- **Reciprocity Validation**: Checks for return tag (A→B, B→A) consistency.
- **ISO Code Verification**: Validates language (ISO 639-1) and region (ISO 3166-1) codes.
- **Sitemap Integration**: Generates hreflang XML sitemap snippets.
- **Protocol & Canonical Checks**: Ensures alignment between hreflang and canonical URLs.

## 9. Visual & Performance Analysis (`/seo visual`, `/seo images`)
Ensures a fast, high-quality user experience.
- **Multi-Viewport Screenshots**: Automated captures for Desktop and Mobile (Playwright required).
- **Above-the-Fold Analysis**: Verifies CTA and H1 visibility without scrolling.
- **Image Optimization**: Detects oversized images, missing alt text, and missing dimensions (CLS prevention).
- **Modern Formats**: Recommends WebP/AVIF and responsive `srcset` implementation.

## 10. Sitemap Architecture (`/seo sitemap`)
- **XML Validation**: Format, URL count, and status code verification.
- **Sitemap Generation**: Interactive generation with industry-specific templates.
- **Quality Gates**: Hard stops and warnings for excessive location/templated pages.
- **lastmod Accuracy**: Verifies sitemap freshness against actual page updates.

---
*Last updated: February 12, 2026*
