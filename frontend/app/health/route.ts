export async function GET() {
  return new Response('ok', { status: 200, headers: { 'content-type': 'text/plain' } })
}

export async function HEAD() {
  return new Response(null, { status: 200 })
}