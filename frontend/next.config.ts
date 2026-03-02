// 2025-02-26
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/api/**" },
      { protocol: "https", hostname: "api.telegram.org", pathname: "/file/**" },
    ],
  },
};

export default nextConfig;
