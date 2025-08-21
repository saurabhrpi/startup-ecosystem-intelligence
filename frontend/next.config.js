/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Use Railway backend for both development and production
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app';
    // Avoid logging secrets/config in production
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig