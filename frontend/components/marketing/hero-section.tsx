import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, BarChart3, ShieldCheck, Zap } from "lucide-react";

export function HeroSection() {
  return (
    <section className="py-20">
      <div className="container mx-auto px-4 text-center">
        <div className="mx-auto max-w-4xl">
          <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            AI-Powered SEO Analysis
            <span className="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
              {" "}for Modern Websites
            </span>
          </h1>
          <p className="mb-8 text-lg text-muted-foreground sm:text-xl">
            Comprehensive SEO audits with parallel processing. Get actionable insights in minutes,
            not hours. Pay only for what you analyze with credit-based pricing.
          </p>
          <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
            <Link href="#audit">
              <Button size="lg">
                Start Free Audit
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/features">
              <Button size="lg" variant="outline">
                View All Features
              </Button>
            </Link>
          </div>
        </div>

        {/* Feature Highlights */}
        <div className="mt-16 grid gap-8 md:grid-cols-3">
          <div className="flex flex-col items-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Lightning Fast</h3>
            <p className="text-center text-muted-foreground">
              Parallel processing across 6 specialized agents delivers results in minutes
            </p>
          </div>
          <div className="flex flex-col items-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <ShieldCheck className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Credit-Based</h3>
            <p className="text-center text-muted-foreground">
              Pay only for what you use. No subscriptions, no monthly fees
            </p>
          </div>
          <div className="flex flex-col items-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <BarChart3 className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Comprehensive</h3>
            <p className="text-center text-muted-foreground">
              10 feature categories cover every aspect of modern SEO
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
