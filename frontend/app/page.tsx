import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { headers } from 'next/headers'
import { authOptions } from '@/lib/auth'
import HomeClient from '@/components/HomeClient'

export default async function Home() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/signin')
  // Fetch initial stats on the server to avoid client-side number flicker
  const hdrs = headers()
  const host = hdrs.get('host') || 'localhost:3000'
  const protocol = process.env.NODE_ENV === 'development' ? 'http' : 'https'
  const base = `${protocol}://${host}`
  const res = await fetch(`${base}/api/stats`, { headers: { Accept: 'application/json' }, cache: 'no-store' })
  const initialStats = res.ok
    ? await res.json()
    : { total_companies: 0, total_embeddings: 0, data_sources: 6 }
  // Fetch user preferences (optional, do not block)
  let initialPrefs: any = { location_code: null, industries: [] }
  try {
    const prefsRes = await fetch(`${base}/api/user/preferences`, { headers: { Accept: 'application/json' }, cache: 'no-store' })
    if (prefsRes.ok) initialPrefs = await prefsRes.json()
  } catch {}
  return <HomeClient initialStats={initialStats} initialPrefs={initialPrefs} />
}