/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Use localhost for development, production URL for production
    const isDev = process.env.NODE_ENV === 'development';
    const apiUrl = isDev 
      ? 'http://localhost:8000' 
      : (process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-intelligence.onrender.com');
    console.log('🔧 API URL in next.config.js:', apiUrl);
    console.log('🌍 NODE_ENV:', process.env.NODE_ENV);
    console.log('🔄 Setting up proxy: /api/backend/* -> ${apiUrl}/*');
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig