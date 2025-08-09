import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const method = request.method
  const userAgent = (request.headers.get('user-agent') || '').toLowerCase()

  const isHealthChecker = userAgent.includes('replit') || userAgent.includes('health') || userAgent.includes('probe')

  if (pathname === '/' && (method === 'HEAD' || (method === 'GET' && isHealthChecker))) {
    return new Response(null, { status: 200 })
  }

  return NextResponse.next()
}