import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Zap, FileSearch, Globe } from "lucide-react";
import { Metadata } from "next";

// Credit pricing constants
const CREDITS_PER_DOLLAR = 8;
const MINIMUM_TOPUP = 8;

// Page metadata for SEO
export const metadata: Metadata = {
  title: "Pricing - SEO Pro",
  description: "Simple, credit-based pricing for SEO analysis. $1 = 8 credits. Pay only for what you analyze.",
  keywords: ["SEO pricing", "website audit cost", "SEO analysis credits", "credit-based SEO"],
  openGraph: {
    title: "SEO Pro Pricing",
    description: "Simple, credit-based pricing for SEO analysis. $1 = 8 credits.",
    type: "website",
  },
};

const analysisTiers = [
  {
    name: "Quick Analysis",
    icon: Zap,
    credits: 1,
    description: "Single analysis type",
    examples: ["Technical SEO", "Content Quality", "Schema Markup"],
    priceNote: "per report",
  },
  {
    name: "Full Page Audit",
    icon: FileSearch,
    credits: 8,
    description: "All 12 analysis types",
    examples: ["One page, complete analysis", "Bundle discount: 33% off"],
    priceNote: "per page",
    popular: true,
  },
  {
    name: "Full Site Audit",
    icon: Globe,
    credits: 7,
    description: "All 12 types × pages",
    examples: ["10 pages = 70 credits", "100 pages = 700 credits"],
    priceNote: "per page",
  },
];

const creditPackages = [
  { credits: 64, price: 8, label: "Starter" },
  { credits: 160, price: 20, label: "Pro", popular: true },
  { credits: 400, price: 50, label: "Business" },
  { credits: 800, price: 100, label: "Enterprise" },
];

export default function PricingPage() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold">Simple, Credit-Based Pricing</h1>
          <p className="text-lg text-muted-foreground">
            $1 = {CREDITS_PER_DOLLAR} credits. Pay only for what you analyze. No subscriptions.
          </p>
        </div>

        {/* Analysis Pricing */}
        <div className="mb-12">
          <h2 className="mb-6 text-2xl font-bold text-center">Analysis Pricing</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {analysisTiers.map((tier) => (
              <Card
                key={tier.name}
                className={`relative ${
                  tier.popular
                    ? "border-primary shadow-lg"
                    : "border-border"
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary px-3 py-1 text-xs font-semibold">
                      Most Popular
                    </Badge>
                  </div>
                )}
                <CardHeader className="text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                    <tier.icon className="h-6 w-6 text-primary" />
                  </div>
                  <CardTitle className="text-xl">{tier.name}</CardTitle>
                  <div className="mt-2">
                    <span className="text-4xl font-bold">{tier.credits}</span>
                    <span className="text-muted-foreground"> credits</span>
                  </div>
                  <CardDescription className="mt-2">
                    {tier.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {tier.examples.map((example) => (
                      <li key={example} className="flex items-start gap-2">
                        <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                        <span className="text-sm">{example}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="pt-2 text-center text-sm text-muted-foreground">
                    ${(tier.credits / CREDITS_PER_DOLLAR).toFixed(2)} {tier.priceNote}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Credit Packages */}
        <div className="mb-12">
          <h2 className="mb-6 text-2xl font-bold text-center">Buy Credits</h2>
          <div className="grid gap-4 md:grid-cols-4">
            {creditPackages.map((pkg) => (
              <Card
                key={pkg.label}
                className={`text-center ${pkg.popular ? "border-primary" : ""}`}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">{pkg.label}</CardTitle>
                  {pkg.popular && (
                    <Badge className="mx-auto mt-1" variant="secondary">Best Value</Badge>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">${pkg.price}</div>
                  <div className="text-sm text-muted-foreground">{pkg.credits} credits</div>
                </CardContent>
              </Card>
            ))}
          </div>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Minimum purchase: ${MINIMUM_TOPUP} (64 credits) • No upper limit
          </p>
        </div>

        {/* All Features Included */}
        <div className="mb-12">
          <h2 className="mb-6 text-2xl font-bold text-center">12 Analysis Types Included</h2>
          <div className="grid gap-3 md:grid-cols-4 text-left">
            {[
              "Technical SEO",
              "Content Quality (E-E-A-T)",
              "Schema Markup",
              "AI Search Optimization",
              "Sitemap Analysis",
              "International SEO",
              "Image Optimization",
              "Visual Analysis",
              "Core Web Vitals",
              "Strategic SEO Planning",
              "Programmatic SEO",
              "Competitor Comparison",
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0" />
                <span className="text-sm">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ */}
        <div className="mb-12">
          <h2 className="mb-6 text-2xl font-bold text-center">
            Frequently Asked Questions
          </h2>
          <div className="mx-auto max-w-3xl space-y-4">
            {[
              {
                q: "How are credits calculated?",
                a: `Individual report: 1 credit ($0.125). Full page audit: 8 credits ($1.00) for all 12 types. Full site audit: 7 credits per page. $1 = ${CREDITS_PER_DOLLAR} credits.`,
              },
              {
                q: "What's the bundle discount?",
                a: "A full page audit includes all 12 analysis types at 8 credits. If you ran each individually, it would cost 12 credits. That's a 33% discount!",
              },
              {
                q: "Do credits expire?",
                a: "No! Credits never expire. Use them whenever you want.",
              },
              {
                q: "What's the minimum purchase?",
                a: `Minimum topup is $${MINIMUM_TOPUP} (64 credits). This gives you 8 full page audits or 64 individual reports.`,
              },
            ].map((item) => (
              <Card key={item.q}>
                <CardHeader>
                  <CardTitle className="text-base">{item.q}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{item.a}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center">
          <Card className="mx-auto max-w-2xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white">
            <CardContent className="py-8">
              <h3 className="mb-4 text-2xl font-bold">Ready to analyze your site?</h3>
              <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
                <Link href="/" className="flex-1">
                  <Button
                    size="lg"
                    variant="secondary"
                    className="w-full bg-white text-primary hover:bg-white/90"
                  >
                    Start Analysis
                  </Button>
                </Link>
                <Link href="/credits" className="flex-1">
                  <Button
                    size="lg"
                    className="w-full border-white bg-white/10 text-white hover:bg-white/20"
                  >
                    Buy Credits
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
