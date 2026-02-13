import Link from "next/link";
import { ShieldCheck, BarChart3, Zap, Globe2, Code2, FileSearch, Layout, Image, Target, XmlTree } from "lucide-react";
import { Metadata } from "next";

const categories = [
  {
    title: "Full Website Audit",
    description: "Parallel analysis across 6 specialized agents covering all SEO aspects.",
    icon: BarChart3,
    color: "from-blue-600 to-cyan-500",
  },
  {
    title: "Technical SEO",
    description: "Core Web Vitals, security headers, crawlability, canonical tags, and mobile optimization.",
    icon: ShieldCheck,
    color: "from-green-600 to-emerald-500",
  },
  {
    title: "Content Quality (E-E-A-T)",
    description: "Experience, Expertise, Authoritativeness, and Trustworthiness scoring based on 2025 guidelines.",
    icon: FileSearch,
    color: "from-purple-600 to-pink-500",
  },
  {
    title: "Schema Markup",
    description: "JSON-LD detection, validation, and generation for rich results. Avoid deprecated types.",
    icon: Code2,
    color: "from-orange-600 to-amber-500",
  },
  {
    title: "AI Search Optimization",
    description: "Optimize for Google AI Overviews, ChatGPT, and Perplexity with citability scoring.",
    icon: Zap,
    color: "from-indigo-600 to-violet-500",
  },
  {
    title: "Sitemap Architecture",
    description: "XML validation, lastmod checks, and proper indexing structure analysis.",
    icon: XmlTree,
    color: "from-teal-600 to-cyan-500",
  },
  {
    title: "International SEO",
    description: "Hreflang validation, ISO code verification, and cross-language link checking.",
    icon: Globe2,
    color: "from-red-600 to-rose-500",
  },
  {
    title: "Visual & Performance",
    description: "Multi-viewport screenshots, above-the-fold analysis, and Core Web Vitals measurement.",
    icon: Layout,
    color: "from-pink-600 to-rose-500",
  },
  {
    title: "Image Optimization",
    description: "Detect oversized images, missing alt text, and recommend modern formats.",
    icon: Image,
    color: "from-sky-600 to-blue-500",
  },
  {
    title: "Programmatic SEO",
    description: "Safeguards and strategies for building SEO pages at scale without penalties.",
    icon: Target,
    color: "from-yellow-600 to-orange-500",
  },
  {
    title: "Competitor Comparison",
    description: "Tools for creating high-converting comparison and alternatives pages.",
    icon: BarChart3,
    color: "from-slate-600 to-gray-500",
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
          10 feature categories covering every aspect of modern SEO. Available from day one
          with credit-based pricing.
        </p>
      </div>

      {/* Feature Categories */}
      <div className="mb-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {categories.map((category) => (
          <Link
            key={category.title}
            href="/"
            className="group"
          >
            <div className="h-full rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md hover:shadow-lg">
              <div
                className={`mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br ${category.color} text-white`}
              >
                <category.icon className="h-6 w-6" />
              </div>
              <h3 className="mb-2 text-lg font-semibold group-hover:text-primary">
                {category.title}
              </h3>
              <p className="text-sm text-muted-foreground">
                {category.description}
              </p>
            </div>
          </Link>
        ))}
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
              title: "Enter Your URL",
              description: "Get a free cost estimate before committing. See page count and credit requirement.",
            },
            {
              step: "2",
              title: "Purchase Credits",
              description: "Buy credits starting at $5. Credits never expire - use them anytime.",
            },
            {
              step: "3",
              title: "Run Analysis",
              description: "6 specialized agents analyze your site in parallel. Results in minutes.",
            },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground text-2xl font-bold">
                {item.step}
              </div>
              <h3 className="mb-2 text-lg font-semibold">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing Preview */}
      <div className="text-center">
        <Link href="/pricing">
          <button className="rounded-lg bg-primary px-8 py-3 text-lg font-semibold text-primary-foreground hover:bg-primary/90">
            View Pricing
          </button>
        </Link>
      </div>
    </div>
  );
}
