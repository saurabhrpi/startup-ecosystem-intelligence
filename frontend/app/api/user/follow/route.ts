import { NextRequest } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const userId = (session?.user as any)?.id || ''
  const userEmail = (session?.user as any)?.email || ''
  const body = await req.text()
  const ts = Date.now().toString()
  // best-effort browser HMAC
  // @ts-ignore
  const subtle: SubtleCrypto | undefined = (globalThis.crypto as any)?.subtle
  let sig = ''
  try {
    if (subtle && apiKey) {
      const enc = new TextEncoder()
      const key = await subtle.importKey('raw', enc.encode(apiKey), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
      const signature = await subtle.sign('HMAC', key, enc.encode(`${userId}.${userEmail}.${ts}`))
      sig = Array.from(new Uint8Array(signature)).map(b => b.toString(16).padStart(2, '0')).join('')
    }
  } catch {}
  const res = await fetch(`${apiUrl}/users/me/follow`, {
    method: 'POST',
    headers: { 'x-api-key': apiKey, 'Accept': 'application/json', 'Content-Type': 'application/json', 'x-user-id': userId, 'x-user-email': userEmail, 'x-user-ts': ts, 'x-user-sig': sig },
    body,
    cache: 'no-store'
  })
  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}


