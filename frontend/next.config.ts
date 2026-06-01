import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' https://spa.k8.ru https://spa2.k8.ru https://sweet.k8.ru https://tilda.cc;",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
