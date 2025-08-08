/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Use Railway backend for both development and production
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app';
    console.log('🔧 API URL in next.config.js:', apiUrl);
    console.log('🌍 NODE_ENV:', process.env.NODE_ENV);
    console.log(`🔄 Setting up proxy: /api/backend/* -> ${apiUrl}/*`);
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig