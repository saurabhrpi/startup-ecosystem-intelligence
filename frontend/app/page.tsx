import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import HomeClient from '@/components/HomeClient'

export default async function Home() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/signin')
  // Fetch initial stats on the server to avoid client-side number flicker
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://startup-ecosystem-api-production.up.railway.app'
  const res = await fetch(`${apiUrl}/ecosystem-stats`, { headers: { Accept: 'application/json' }, cache: 'no-store' })
  const initialStats = res.ok
    ? await res.json()
    : { total_companies: 0, total_embeddings: 0, data_sources: 6 }
  return <HomeClient initialStats={initialStats} />
}