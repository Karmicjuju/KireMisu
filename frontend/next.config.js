/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost', '127.0.0.1'],
    formats: ['image/avif', 'image/webp'],
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  // Only use standalone output for production builds
  ...(process.env.NODE_ENV === 'production' && { output: 'standalone' }),
};

module.exports = nextConfig;
