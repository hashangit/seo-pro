import { PurchaseCredits } from "@/components/credits/purchase-credits";

export default function CreditsPage() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-8 text-3xl font-bold">Purchase Credits</h1>
        <PurchaseCredits />
      </div>
    </div>
  );
}
