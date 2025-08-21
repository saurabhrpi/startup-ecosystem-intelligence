import { NextRequest } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { createHmac } from 'crypto'

function signUser(id: string, email: string, secret: string) {
  const ts = Date.now().toString()
  const payload = `${id}.${email}.${ts}`
  const sig = secret ? createHmac('sha256', secret).update(payload).digest('hex') : ''
  return { ts, sig }
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

  const { ts, sig } = signUser(userId, userEmail, apiKey)

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

  const { ts, sig } = signUser(userId, userEmail, apiKey)

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


