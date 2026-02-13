import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2 } from "lucide-react";
import { Metadata } from "next";

// Get credit rate from environment to avoid hardcoding
const CREDIT_RATE_LKR = parseInt(process.env.NEXT_PUBLIC_PAYHERE_CREDIT_RATE_LKR || "350", 10);

// Page metadata for SEO
export const metadata: Metadata = {
  title: "Pricing - SEO Pro",
  description: "Simple, credit-based pricing for SEO analysis. See our affordable pricing tiers.",
  keywords: ["SEO pricing", "website audit cost", "SEO analysis credits", "PayHere credits"],
  openGraph: {
    title: "SEO Pro Pricing",
    description: "Simple, credit-based pricing for SEO analysis",
    type: "website",
  },
}; // Rs. 350 per credit

const pricingTiers = [
  {
    name: "Starter",
    pages: "1",
    credits: 3,
    usd: 3,
    lkr: 3 * CREDIT_RATE_LKR,
    description: "Perfect for single page analysis",
  },
  {
    name: "Standard",
    pages: "Up to 10",
    credits: 5,
    usd: 5,
    lkr: 5 * CREDIT_RATE_LKR,
    description: "Best value for small sites",
  },
  {
    name: "Growing",
    pages: "20 pages",
    credits: 7,
    usd: 7,
    lkr: 7 * CREDIT_RATE_LKR,
    description: "For expanding websites",
    popular: true,
  },
  {
    name: "Business",
    pages: "50 pages",
    credits: 13,
    usd: 13,
    lkr: 13 * CREDIT_RATE_LKR,
    description: "Comprehensive site audit",
  },
];

export default function PricingPage() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold">Simple, Credit-Based Pricing</h1>
          <p className="text-lg text-muted-foreground">
            Pay only for what you analyze. No subscriptions, no monthly fees.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="mb-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.name}
              className={`relative ${
                tier.popular
                  ? "border-primary shadow-lg scale-105"
                  : "border-border"
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
                    Most Popular
                  </span>
                </div>
              )}
              <CardHeader>
                <CardTitle className="text-xl">{tier.name}</CardTitle>
                <div className="mt-2 text-3xl font-bold">
                  ${tier.usd}
                </div>
                <CardDescription className="mt-2">
                  {tier.pages} pages
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-2">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">{tier.description}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <span className="text-sm">
                      Rs. {tier.lkr.toLocaleString()} (~${tier.usd} USD)
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <span className="text-sm">Credits never expire</span>
                  </li>
                </ul>

                <Link href="/credits/purchase" className="block">
                  <Button className="w-full" variant={tier.popular ? "default" : "outline"}>
                    Purchase Credits
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Custom Pricing */}
        <Card className="mb-12">
          <CardHeader>
            <CardTitle>Custom Analysis</CardTitle>
            <CardDescription>
              For sites with more than 50 pages
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Large sites are priced at 2 credits per additional 10 pages.
              The first 10 pages cost 5 credits, then each additional
              10-page block costs 2 credits.
            </p>
            <Link href="/credits/purchase">
              <Button className="w-full" variant="outline">
                Buy Custom Credits
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Features */}
        <div className="text-center">
          <h2 className="mb-6 text-2xl font-bold">Everything Included</h2>
          <div className="grid gap-4 md:grid-cols-3 text-left">
            {[
              "Technical SEO Analysis",
              "Content Quality (E-E-A-T)",
              "Schema Markup Detection",
              "AI Search Optimization",
              "Sitemap Architecture",
              "International SEO",
              "Visual Analysis",
              "Performance Metrics",
              "Image Optimization",
            ].map((feature) => (
              <div key={feature} className="flex items-start gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <span className="text-sm">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-12">
          <h2 className="mb-6 text-2xl font-bold text-center">
            Frequently Asked Questions
          </h2>
          <div className="mx-auto max-w-3xl space-y-4">
            {[
              {
                q: "How are credits calculated?",
                a: "1 page = 3 credits, 10 pages = 5 credits, additional 10-page blocks = 2 credits each.",
              },
              {
                q: "Do credits expire?",
                a: "No! Credits never expire. Use them whenever you want.",
              },
              {
                q: "What payment methods do you accept?",
                a: "We accept PayHere (Sri Lanka) which supports VISA, MasterCard, AMEX, and mobile wallets like eZ cash, mCash, and Genie.",
              },
              {
                q: "Can I get a refund?",
                a: "Due to the nature of SEO analysis services, refunds are not available once an audit has been initiated.",
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
        <div className="mt-12 text-center">
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
                    Start Free Audit
                  </Button>
                </Link>
                <Link href="/credits/purchase" className="flex-1">
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
