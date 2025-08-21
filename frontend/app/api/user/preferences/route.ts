import { NextRequest } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

function buildSigHeaders(id: string, email: string, apiKey: string) {
  const ts = Date.now().toString()
  return { ts, payload: `${id}.${email}.${ts}` }
}

async function hmacHex(key: string, payload: string) {
  try {
    // @ts-ignore
    const subtle: SubtleCrypto | undefined = (globalThis.crypto as any)?.subtle
    if (!subtle || !key) return ''
    const enc = new TextEncoder()
    const k = await subtle.importKey('raw', enc.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
    const sig = await subtle.sign('HMAC', k, enc.encode(payload))
    return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')
  } catch { return '' }
}

export async function GET(_req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const userId = (session?.user as any)?.id || ''
  const userEmail = (session?.user as any)?.email || ''
  const { ts, payload } = buildSigHeaders(userId, userEmail, apiKey)
  const sig = await hmacHex(apiKey, payload)
  const res = await fetch(`${apiUrl}/users/me/preferences`, {
    headers: { 'x-api-key': apiKey, 'Accept': 'application/json', 'x-user-id': userId, 'x-user-email': userEmail, 'x-user-ts': ts, 'x-user-sig': sig },
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
  const userEmail = (session?.user as any)?.email || ''
  const body = await req.text()
  const { ts, payload } = buildSigHeaders(userId, userEmail, apiKey)
  const sig = await hmacHex(apiKey, payload)
  const res = await fetch(`${apiUrl}/users/me/preferences`, {
    method: 'PUT',
    headers: { 'x-api-key': apiKey, 'Accept': 'application/json', 'Content-Type': 'application/json', 'x-user-id': userId, 'x-user-email': userEmail, 'x-user-ts': ts, 'x-user-sig': sig },
    body,
    cache: 'no-store',
  })
  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}


