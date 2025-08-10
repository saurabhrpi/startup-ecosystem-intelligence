import { NextRequest } from 'next/server'

export async function GET(req: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''

  const { search } = new URL(req.url)
  const url = `${apiUrl}/search${search}`

  const res = await fetch(url, {
    headers: {
      'x-api-key': apiKey,
      'Accept': 'application/json',
    },
    cache: 'no-store',
  })

  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}

export async function POST(req: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const apiKey = process.env.BACKEND_API_KEY || ''
  const body = await req.text()

  const res = await fetch(`${apiUrl}/search`, {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body,
    cache: 'no-store',
  })

  return new Response(await res.text(), { status: res.status, headers: { 'content-type': 'application/json' } })
}


