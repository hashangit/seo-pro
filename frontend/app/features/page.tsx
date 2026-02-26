import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ShieldCheck, BarChart3, Zap, Globe2, Code2, FileSearch, Layout, Image, Target, XmlTree, Play } from "lucide-react";
import { Metadata } from "next";

const categories = [
  {
    title: "Full Website Audit",
    description: "Parallel analysis across 6 specialized agents covering all SEO aspects.",
    icon: BarChart3,
    color: "from-blue-600 to-cyan-500",
    analysisType: null, // Site audit
    credits: "7/page",
  },
  {
    title: "Technical SEO",
    description: "Core Web Vitals, security headers, crawlability, canonical tags, and mobile optimization.",
    icon: ShieldCheck,
    color: "from-green-600 to-emerald-500",
    analysisType: "technical",
    credits: "1",
  },
  {
    title: "Content Quality (E-E-A-T)",
    description: "Experience, Expertise, Authoritativeness, and Trustworthiness scoring based on 2025 guidelines.",
    icon: FileSearch,
    color: "from-purple-600 to-pink-500",
    analysisType: "content",
    credits: "1",
  },
  {
    title: "Schema Markup",
    description: "JSON-LD detection, validation, and generation for rich results. Avoid deprecated types.",
    icon: Code2,
    color: "from-orange-600 to-amber-500",
    analysisType: "schema",
    credits: "1",
  },
  {
    title: "AI Search Optimization",
    description: "Optimize for Google AI Overviews, ChatGPT, and Perplexity with citability scoring.",
    icon: Zap,
    color: "from-indigo-600 to-violet-500",
    analysisType: "geo",
    credits: "1",
  },
  {
    title: "Sitemap Architecture",
    description: "XML validation, lastmod checks, and proper indexing structure analysis.",
    icon: XmlTree,
    color: "from-teal-600 to-cyan-500",
    analysisType: "sitemap",
    credits: "1",
  },
  {
    title: "International SEO",
    description: "Hreflang validation, ISO code verification, and cross-language link checking.",
    icon: Globe2,
    color: "from-red-600 to-rose-500",
    analysisType: "hreflang",
    credits: "1",
  },
  {
    title: "Visual & Performance",
    description: "Multi-viewport screenshots, above-the-fold analysis, and Core Web Vitals measurement.",
    icon: Layout,
    color: "from-pink-600 to-rose-500",
    analysisType: null,
    credits: "2",
  },
  {
    title: "Image Optimization",
    description: "Detect oversized images, missing alt text, and recommend modern formats.",
    icon: Image,
    color: "from-sky-600 to-blue-500",
    analysisType: "images",
    credits: "1",
  },
  {
    title: "Programmatic SEO",
    description: "Safeguards and strategies for building SEO pages at scale without penalties.",
    icon: Target,
    color: "from-yellow-600 to-orange-500",
    analysisType: "programmatic",
    credits: "1",
  },
  {
    title: "Competitor Comparison",
    description: "Analyze your 'X vs Y' and 'Alternatives to X' pages for SEO, GEO, and AEO.",
    icon: BarChart3,
    color: "from-slate-600 to-gray-500",
    analysisType: "competitor-pages",
    credits: "1",
  },
];

export default function FeaturesPage() {
  return (
    <div className="container mx-auto px-4 py-12">
      {/* Header */}
      <div className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold">
          Comprehensive SEO Analysis
        </h1>
        <p className="text-lg text-muted-foreground">
          12 analysis types covering every aspect of modern SEO.
          Run individual reports or comprehensive audits.
        </p>
        <p className="mt-2 text-sm text-primary font-medium">
          $1 = 8 credits • Individual reports: 1 credit • Full page audit: 8 credits
        </p>
      </div>

      {/* Feature Categories */}
      <div className="mb-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {categories.map((category) => (
          <div
            key={category.title}
            className="group h-full rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md"
          >
            <div className="flex items-start justify-between">
              <div
                className={`mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br ${category.color} text-white`}
              >
                <category.icon className="h-6 w-6" />
              </div>
              <span className="rounded-full bg-muted px-2 py-1 text-xs font-medium">
                {category.credits} credit{category.credits !== "1" ? "" : ""}
              </span>
            </div>
            <h3 className="mb-2 text-lg font-semibold">
              {category.title}
            </h3>
            <p className="mb-4 text-sm text-muted-foreground">
              {category.description}
            </p>
            <Link href={`/?type=${category.analysisType || "site"}`}>
              <Button variant="outline" size="sm" className="w-full group-hover:bg-primary group-hover:text-primary-foreground">
                <Play className="mr-2 h-3 w-3" />
                Run Analysis
              </Button>
            </Link>
          </div>
        ))}
      </div>

      {/* Analysis Modes */}
      <div className="mb-12">
        <h2 className="mb-6 text-2xl font-bold text-center">
          Three Ways to Analyze
        </h2>
        <div className="mx-auto max-w-4xl grid gap-6 md:grid-cols-3">
          {[
            {
              title: "Quick Analysis",
              price: "1 credit",
              description: "Run individual reports on specific aspects. Perfect for targeted optimizations.",
            },
            {
              title: "Full Page Audit",
              price: "8 credits",
              description: "All 12 analysis types on one page. Bundle discount: 33% off vs individual.",
              highlight: true,
            },
            {
              title: "Full Site Audit",
              price: "7 credits/page",
              description: "Complete website analysis. Volume discount for larger sites.",
            },
          ].map((mode) => (
            <div
              key={mode.title}
              className={`rounded-lg border p-6 text-center ${
                mode.highlight ? "border-primary bg-primary/5" : ""
              }`}
            >
              {mode.highlight && (
                <span className="mb-2 inline-block rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
                  Most Popular
                </span>
              )}
              <h3 className="mb-2 text-lg font-semibold">{mode.title}</h3>
              <p className="mb-3 text-2xl font-bold text-primary">{mode.price}</p>
              <p className="text-sm text-muted-foreground">{mode.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works */}
      <div className="mb-12">
        <h2 className="mb-6 text-2xl font-bold text-center">
          How It Works
        </h2>
        <div className="mx-auto max-w-4xl grid gap-6 md:grid-cols-3">
          {[
            {
              step: "1",
              title: "Choose Analysis",
              description: "Select individual reports, full page audit, or site-wide audit.",
            },
            {
              step: "2",
              title: "Get Estimate",
              description: "See the exact credit cost before you commit. No surprises.",
            },
            {
              step: "3",
              title: "Run & Review",
              description: "Specialized agents analyze your site. Get actionable recommendations.",
            },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground text-2xl font-bold mx-auto">
                {item.step}
              </div>
              <h3 className="mb-2 text-lg font-semibold">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="text-center">
        <Link href="/">
          <Button size="lg" className="px-8">
            Start Your Analysis
          </Button>
        </Link>
      </div>
    </div>
  );
}
