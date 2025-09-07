import { NextRequest } from 'next/server'

export async function GET(_req: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const res = await fetch(`${apiUrl}/ecosystem-stats`, { headers: { Accept: 'application/json' }, cache: 'no-store' })
  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}


