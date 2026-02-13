import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export function CTASection() {
  return (
    <section className="py-20">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-3xl rounded-2xl bg-gradient-to-r from-blue-600 to-cyan-500 p-12 text-center text-white">
          <h2 className="mb-4 text-3xl font-bold">
            Ready to Improve Your SEO?
          </h2>
          <p className="mb-8 text-lg text-blue-50">
            Get a comprehensive SEO audit in minutes. No subscription required.
            Pay only for what you analyze with credit-based pricing.
          </p>
          <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
            <Link href="#audit">
              <Button size="lg" variant="secondary">
                Start Your Audit
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/pricing">
              <Button size="lg" variant="outline" className="bg-white/10 text-white hover:bg-white/20">
                View Pricing
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
