import type { NextConfig } from "next";
import path from "path";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  /* config options here */
  reactStrictMode: true,
  basePath: isProd ? "/FinFit-ui" : "",
  assetPrefix: isProd ? "/FinFit-ui/" : "",
  images: {
    unoptimized: true,
  },
  output: "export",
  env: {
    NEXT_PUBLIC_BASE_PATH: isProd ? "/FinFit-ui" : "",
  },
  sassOptions: {
    includePaths: [path.join(__dirname, "node_modules")],
  },
};

export default nextConfig;

