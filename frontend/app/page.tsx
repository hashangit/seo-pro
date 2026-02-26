import { AnalysisSelector } from "@/components/analysis/analysis-selector";
import { FeaturesGrid } from "@/components/marketing/features-grid";
import { CTASection } from "@/components/marketing/cta-section";
import { HeroSection } from "@/components/marketing/hero-section";

export default function HomePage() {
  return (
    <div className="flex flex-col">
      <HeroSection />
      <FeaturesGrid />
      <section className="py-20 bg-muted/50">
        <div className="container mx-auto px-4">
          <AnalysisSelector />
        </div>
      </section>
      <CTASection />
    </div>
  );
}
