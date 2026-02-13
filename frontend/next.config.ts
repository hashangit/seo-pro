import type { NextConfig } from "next";

const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
const NEXT_PUBLIC_WORKOS_CLIENT_ID = process.env.NEXT_PUBLIC_WORKOS_CLIENT_ID || "";
const NEXT_PUBLIC_WORKOS_REDIRECT_URI = process.env.NEXT_PUBLIC_WORKOS_REDIRECT_URI || "";

const nextConfig: NextConfig = {
  experimental: {
    turbo: {
      rules: {
        "*.svg": {
          loaders: ["@svgr/webpack"],
          as: "*.js",
        },
      },
    },
  },
  env: {
    NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WORKOS_CLIENT_ID,
    NEXT_PUBLIC_WORKOS_REDIRECT_URI,
  },
};

export default nextConfig;
