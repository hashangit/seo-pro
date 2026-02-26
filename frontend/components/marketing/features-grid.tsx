import {
  BarChart3,
  Code2,
  CodeXml,
  FileSearch,
  Globe2,
  Image,
  Layout,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";

const features = [
  {
    name: "Technical SEO",
    description: "Deep technical analysis including Core Web Vitals, security headers, crawlability, and mobile optimization.",
    icon: ShieldCheck,
  },
  {
    name: "Content Quality (E-E-A-T)",
    description: "Evaluate content based on Google's 2025 Quality Rater Guidelines with experience, expertise, authoritativeness, and trustworthiness scoring.",
    icon: FileSearch,
  },
  {
    name: "Schema Markup",
    description: "Detect, validate, and generate JSON-LD schema for rich results. Avoid deprecated types.",
    icon: Code2,
  },
  {
    name: "AI Search Optimization",
    description: "Optimize for Google AI Overviews, ChatGPT, and Perplexity with citability scoring.",
    icon: Sparkles,
  },
  {
    name: "Sitemap Architecture",
    description: "Analyze XML sitemaps, validate structure, and ensure proper indexing.",
    icon: CodeXml,
  },
  {
    name: "International SEO",
    description: "Hreflang validation, ISO code verification, and cross-language link checking.",
    icon: Globe2,
  },
  {
    name: "Visual Analysis",
    description: "Multi-viewport screenshots, above-the-fold CTA visibility, and mobile rendering checks.",
    icon: Layout,
  },
  {
    name: "Image Optimization",
    description: "Detect oversized images, missing alt text, and recommend modern formats.",
    icon: Image,
  },
  {
    name: "Programmatic SEO",
    description: "Safeguards and strategies for building SEO pages at scale without penalties.",
    icon: Target,
  },
  {
    name: "Competitor Comparison",
    description: "Tools for creating high-converting comparison and alternatives pages.",
    icon: BarChart3,
  },
];

export function FeaturesGrid() {
  return (
    <section className="py-20">
      <div className="container mx-auto px-4">
        <div className="mb-12 text-center">
          <h2 className="mb-4 text-3xl font-bold">
            Everything You Need for SEO Success
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            Comprehensive analysis across 10 feature categories. All available from day one
            with credit-based pricing.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.name}
              className="rounded-lg border bg-card p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <feature.icon className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-lg font-semibold">{feature.name}</h3>
              <p className="text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
