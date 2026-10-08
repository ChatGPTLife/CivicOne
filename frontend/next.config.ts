// 2025-02-26
import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Avoid resolving from a parent package-lock (e.g. C:\Users\...\package-lock.json)
  turbopack: {
    root: path.resolve(process.cwd()),
  },
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/api/**" },
      { protocol: "https", hostname: "api.telegram.org", pathname: "/file/**" },
    ],
  },
};

export default nextConfig;
