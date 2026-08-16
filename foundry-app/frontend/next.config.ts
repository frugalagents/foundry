import type { NextConfig } from 'next'

const isProd = process.env.NODE_ENV === 'production'

const config: NextConfig = {
  // Static export for S3/CloudFront hosting
  output: isProd ? 'export' : undefined,
  trailingSlash: true,
  // In static export mode, rewrites don't apply — the frontend calls the
  // Lambda Function URL directly via NEXT_PUBLIC_API_URL.
  // In dev mode, proxy /api/* to the local FastAPI backend.
  ...(isProd
    ? {}
    : {
        async rewrites() {
          const apiUrl = process.env.API_URL ?? 'http://localhost:8000'
          return [
            {
              source: '/api/:path*',
              destination: `${apiUrl}/api/:path*`,
            },
          ]
        },
      }),
}

export default config
