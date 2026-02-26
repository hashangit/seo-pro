import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { ErrorBoundary } from "@/components/error-boundary";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SEO Pro - AI-Powered SEO Analysis",
  description: "Comprehensive SEO analysis with parallel processing and credit-based pricing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const clientId = process.env.NEXT_PUBLIC_WORKOS_CLIENT_ID;
  const redirectUri = process.env.NEXT_PUBLIC_WORKOS_REDIRECT_URI;

  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers clientId={clientId} redirectUri={redirectUri}>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1">
              <ErrorBoundary>
                {children}
              </ErrorBoundary>
            </main>
            <footer className="border-t py-6">
              <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
                <p>&copy; {new Date().getFullYear()} SEO Pro. All rights reserved.</p>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
