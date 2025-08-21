import { NextRequest } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

function signUser(id: string, email: string, secret: string) {
  const ts = Date.now().toString()
  // Simple HMAC SHA256 hex
  const encoder = new TextEncoder()
  const payload = `${id}.${email}.${ts}`
  // @ts-ignore - Node 18+ crypto.subtle available in Next runtime
  const cryptoObj: SubtleCrypto = (globalThis.crypto as any)?.subtle
  // Fallback: no signing if crypto.subtle unavailable; headers will miss sig
  return {
    ts,
    asyncSig: (async () => {
      try {
        if (!cryptoObj || !secret) return ''
        const key = await cryptoObj.importKey(
          'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
        )
        const signature = await cryptoObj.sign('HMAC', key, encoder.encode(payload))
        const bytes = Array.from(new Uint8Array(signature))
        return bytes.map(b => b.toString(16).padStart(2, '0')).join('')
      } catch {
        return ''
      }
    })()
  }
}

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const userId = (session?.user as any)?.id || ''
  const userEmail = (session?.user as any)?.email || ''

  const { search } = new URL(req.url)
  const url = `${apiUrl}/search${search}`

  const { ts, asyncSig } = signUser(userId, userEmail, apiKey)
  const sig = await asyncSig

  const res = await fetch(url, {
    headers: {
      'x-api-key': apiKey,
      'Accept': 'application/json',
      'x-user-id': userId,
      'x-user-email': userEmail,
      'x-user-ts': ts,
      'x-user-sig': sig,
    },
    cache: 'no-store',
  })

  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const userId = (session?.user as any)?.id || ''
  const userEmail = (session?.user as any)?.email || ''
  const body = await req.text()

  const { ts, asyncSig } = signUser(userId, userEmail, apiKey)
  const sig = await asyncSig

  const res = await fetch(`${apiUrl}/search`, {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'x-user-id': userId,
      'x-user-email': userEmail,
      'x-user-ts': ts,
      'x-user-sig': sig,
    },
    body,
    cache: 'no-store',
  })

  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}


