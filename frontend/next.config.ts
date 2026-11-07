import type { NextConfig } from "next";

const apiProxyTarget =
  process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
      {
        source: "/admin/:path*",
        destination: `${apiProxyTarget}/admin/:path*`,
      },
      {
        source: "/static/:path*",
        destination: `${apiProxyTarget}/static/:path*`,
      },
    ];
  },
};

export default nextConfig;
