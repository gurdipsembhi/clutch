import type { NextConfig } from "next";

const apiUrl = process.env.NEXT_PUBLIC_API_URL;

const nextConfig: NextConfig = {
  // Self-contained server bundle for Cloud Run / Docker.
  output: "standalone",
  async rewrites() {
    // Optional same-origin proxy. The app calls the backend directly via
    // NEXT_PUBLIC_API_URL, so this is only a convenience fallback.
    if (!apiUrl) return [];
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;
