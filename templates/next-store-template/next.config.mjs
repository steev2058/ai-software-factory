/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export for factory live deploys
  output: 'export',
  images: { unoptimized: true },
};
export default nextConfig;
