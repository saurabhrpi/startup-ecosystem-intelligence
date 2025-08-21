'use client'

import { useEffect, useState } from 'react'

type Prefs = { location_code?: string | null; industries?: string[] }

export default function SettingsPage() {
  const [locations, setLocations] = useState<Array<{ canonical: string; aliases: string[] }>>([])
  const [industries, setIndustries] = useState<string[]>([])
  const [prefs, setPrefs] = useState<Prefs>({ location_code: null, industries: [] })
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const [locRes, indRes, prefRes] = await Promise.all([
          fetch('/api/backend/catalog/locations', { headers: { Accept: 'application/json' } }),
          fetch('/api/backend/catalog/industries', { headers: { Accept: 'application/json' } }),
          fetch('/api/backend/users/me/preferences', { headers: { Accept: 'application/json' } }),
        ])
        if (locRes.ok) setLocations((await locRes.json()).locations || [])
        if (indRes.ok) setIndustries((await indRes.json()).industries || [])
        if (prefRes.ok) setPrefs(await prefRes.json())
      } catch {}
    }
    load()
  }, [])

  const toggleIndustry = (name: string) => {
    setPrefs((p) => {
      const curr = new Set(p.industries || [])
      if (curr.has(name)) curr.delete(name)
      else curr.add(name)
      return { ...p, industries: Array.from(curr) }
    })
  }

  const save = async () => {
    setSaving(true)
    setSavedOk(false)
    try {
      const res = await fetch('/api/backend/users/me/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location_code: prefs.location_code, industries: prefs.industries || [] }),
      })
      setSavedOk(res.ok)
    } catch {
      setSavedOk(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Personalization</h1>

        <section className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800">Default location</h2>
          <p className="text-sm text-gray-600">Used to bias results when your query doesn’t specify a location.</p>
          <div className="mt-3">
            <select
              className="w-full max-w-sm rounded-lg border border-gray-300 px-3 py-2 text-gray-800"
              value={prefs.location_code || ''}
              onChange={(e) => setPrefs((p) => ({ ...p, location_code: e.target.value || null }))}
            >
              <option value="">None</option>
              {locations.map((l) => (
                <option key={l.canonical} value={l.canonical}>{l.canonical.toUpperCase()}</option>
              ))}
            </select>
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800">Preferred industries</h2>
          <p className="text-sm text-gray-600">Used to bias results when industry isn’t specified.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {industries.map((name) => {
              const active = (prefs.industries || []).includes(name)
              return (
                <button
                  key={name}
                  onClick={() => toggleIndustry(name)}
                  className={`rounded-full border px-3 py-1 text-sm ${active ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-800 border-gray-300'}`}
                >
                  {name}
                </button>
              )
            })}
          </div>
        </section>

        <div className="flex items-center gap-3">
          <button onClick={save} disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-white font-semibold hover:bg-indigo-700 disabled:opacity-50">{saving ? 'Saving…' : 'Save preferences'}</button>
          {savedOk && <span className="text-sm text-green-600">Saved</span>}
        </div>
      </div>
    </main>
  )
}


