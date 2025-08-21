import { NextRequest } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export async function GET(_req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const userId = (session?.user as any)?.id || ''
  const res = await fetch(`${apiUrl}/users/me/preferences`, {
    headers: { 'x-api-key': apiKey, 'Accept': 'application/json', 'x-user-id': userId },
    cache: 'no-store',
  })
  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}

export async function PUT(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const userId = (session?.user as any)?.id || ''
  const body = await req.text()
  const res = await fetch(`${apiUrl}/users/me/preferences`, {
    method: 'PUT',
    headers: { 'x-api-key': apiKey, 'Accept': 'application/json', 'Content-Type': 'application/json', 'x-user-id': userId },
    body,
    cache: 'no-store',
  })
  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}


