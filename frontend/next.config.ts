import type { NextConfig } from 'next';
import path from 'path';

// Backend API URL - use environment variable or default
// In Docker: use 'backend' service name; locally: use 'localhost'
const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || 'http://localhost:8000';

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Set the correct workspace root to avoid lockfile detection issues
  outputFileTracingRoot: path.join(__dirname, './'),

  // Enable experimental features for performance
  experimental: {
    // Optimize package imports for faster loading
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-select',
      '@radix-ui/react-tabs',
      '@radix-ui/react-tooltip',
      'react-syntax-highlighter',
      'react-markdown',
      'remark-gfm',
      'date-fns',
      'sonner',
    ],
  },

  // Enable compiler optimizations
  compiler: {
    // Remove console logs in production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },

  // API proxy for development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
    // Optimize image loading
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    formats: ['image/avif', 'image/webp'],
  },

  // Enable output tracing for smaller builds
  output: process.env.DOCKER_BUILD === 'true' ? 'standalone' : undefined,

  // Webpack optimizations
  webpack: (config, { dev, isServer }) => {
    // Optimize chunks in production
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          minSize: 20000,
          maxSize: 244000,
          cacheGroups: {
            // Separate vendor chunks for better caching
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
              priority: 10,
            },
            // Separate radix-ui into its own chunk
            radix: {
              test: /[\\/]node_modules[\\/]@radix-ui[\\/]/,
              name: 'radix',
              chunks: 'all',
              priority: 20,
            },
            // Separate react-syntax-highlighter (large dependency)
            highlighter: {
              test: /[\\/]node_modules[\\/]react-syntax-highlighter[\\/]/,
              name: 'highlighter',
              chunks: 'all',
              priority: 20,
            },
            markdown: {
              test: /[\\/]node_modules[\\/](react-markdown|remark-|rehype-|unified|mdast-|micromark|hast-)[\\/]/,
              name: 'markdown',
              chunks: 'all',
              priority: 20,
            },
          },
        },
      };
    }
    return config;
  },

  // Headers for better caching
  async headers() {
    return [
      {
        source: '/:all*(svg|jpg|jpeg|png|gif|ico|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
