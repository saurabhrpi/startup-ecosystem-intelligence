'use client'

import { useEffect, useRef, useState } from 'react'
import { signIn } from 'next-auth/react'
import { Sparkles, Mail, Shield, CheckCircle2, ArrowRight, Search, Filter, Share2, Network } from 'lucide-react'

export default function SignInPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'semantic' | 'filters' | 'graph'>('semantic')
  const [cursorPos, setCursorPos] = useState<{ x: number; y: number }>({ x: 150, y: 80 })
  const [stepIndex, setStepIndex] = useState(0)
  const carouselRef = useRef<HTMLDivElement>(null)
  const overlayRef1 = useRef<HTMLDivElement>(null)
  const overlayRef2 = useRef<HTMLDivElement>(null)
  const [overlayActive, setOverlayActive] = useState<'one' | 'two'>('one')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const res = await signIn('credentials', { email, redirect: true, callbackUrl: '/' })
    if (res?.error) setError('Sign-in failed')
    setLoading(false)
  }

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-gradient-to-br from-[#0a0b14] via-[#0c0f1d] to-[#090a12] text-white">
      {/* Background accents */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full mix-blend-screen blur-3xl opacity-30 animate-blob" style={{ background: 'radial-gradient(closest-side, rgba(124,58,237,0.6), transparent)' }} />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full mix-blend-screen blur-3xl opacity-25 animate-blob animation-delay-2000" style={{ background: 'radial-gradient(closest-side, rgba(59,130,246,0.6), transparent)' }} />
        <div className="absolute top-40 left-1/2 -translate-x-1/2 w-80 h-80 rounded-full mix-blend-screen blur-3xl opacity-20 animate-blob animation-delay-4000" style={{ background: 'radial-gradient(closest-side, rgba(236,72,153,0.5), transparent)' }} />
      </div>

      {/* Top bar */}
      <header className="w-full">
        <div className="mx-auto max-w-7xl px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 text-white shadow-md">
              <Sparkles size={18} />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-blue-700 to-purple-700 bg-clip-text text-transparent">
              Startup Ecosystem Intelligence
            </span>
          </div>
        </div>
      </header>

      {/* Content */}
      <section className="mx-auto max-w-7xl px-6 pb-20 pt-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          {/* Left: value prop */}
          <div className="hidden md:block">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
              <Shield size={14} /> Graph-RAG powered insights
            </div>
            <h1 className="mt-4 text-4xl md:text-5xl font-extrabold tracking-tight text-white">
              Discover opportunities in the startup ecosystem
            </h1>
            <p className="mt-4 text-slate-300 max-w-xl">
              Search companies, founders, investors, and repositories with precise filters for batch, industry, and location. No noise—just accurate matches.
            </p>
            <ul className="mt-6 space-y-3 text-slate-200">
              <li className="flex items-start gap-2"><CheckCircle2 className="text-emerald-400 mt-0.5" size={18} /> Filter-only results return exact matches—no drift.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="text-emerald-400 mt-0.5" size={18} /> Recommendations derive strictly from real matches.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="text-emerald-400 mt-0.5" size={18} /> Visualize connections across people, companies, and repos.</li>
            </ul>
          </div>

          {/* Right: sign-in card */}
          <div className="w-full">
            <div className="relative mx-auto w-full max-w-md">
              <div className="absolute -inset-0.5 rounded-3xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-30 blur-lg"></div>
              <div className="relative rounded-3xl border border-white/10 bg-white/[0.06] shadow-2xl backdrop-blur-md p-8">
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white">Sign in</h2>
                  <p className="mt-1 text-sm text-slate-300">Use your email to continue</p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm text-slate-200 mb-1">Email</label>
                    <div className="relative">
                      <div className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400">
                        <Mail size={16} />
                      </div>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full rounded-xl border border-white/10 bg-white/5 px-10 py-3 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                        placeholder="you@example.com"
                      />
                    </div>
                  </div>
                  {error && <p className="text-sm text-red-400">{error}</p>}
                  <button
                    type="submit"
                    disabled={loading}
                    className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50"
                  >
                    {loading ? 'Signing in…' : 'Continue'}
                    <ArrowRight size={16} className="transition group-hover:translate-x-0.5" />
                  </button>
                </form>
                <p className="mt-4 text-xs text-slate-400">
                  By continuing, you agree to our Terms and Privacy Policy.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
      {/* Feature Tabs */}
      <section className="mx-auto max-w-7xl px-6 pb-20">
        <div className="mb-6 flex gap-2">
          <button onClick={() => setActiveTab('semantic')} className={`rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ${activeTab==='semantic' ? 'bg-indigo-600 text-white ring-indigo-500' : 'bg-white/5 text-slate-300 ring-white/10 hover:bg-white/10'}`}>Semantic Search</button>
          <button onClick={() => setActiveTab('filters')} className={`rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ${activeTab==='filters' ? 'bg-indigo-600 text-white ring-indigo-500' : 'bg-white/5 text-slate-300 ring-white/10 hover:bg-white/10'}`}>Filtering</button>
          <button onClick={() => setActiveTab('graph')} className={`rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ${activeTab==='graph' ? 'bg-indigo-600 text-white ring-indigo-500' : 'bg-white/5 text-slate-300 ring-white/10 hover:bg-white/10'}`}>Graph-enabled</button>
        </div>
        <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-xl backdrop-blur-md">
          {activeTab === 'semantic' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div>
                <h3 className="text-xl font-bold">Natural-language understanding</h3>
                <p className="mt-2 text-slate-300">Ask questions like “developer tools with &gt;100 stars” — we extract numeric and entity filters and run hybrid search.</p>
                <ul className="mt-4 space-y-2 text-slate-200">
                  <li className="flex items-center gap-2"><Search size={16} className="text-indigo-400" /> Embedding-driven recall</li>
                  <li className="flex items-center gap-2"><Filter size={16} className="text-indigo-400" /> Precise post-filtering</li>
                </ul>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
                <pre className="text-xs text-slate-200 whitespace-pre-wrap">{`Query: "Developer tools with >100 stars"
Extracted: min_star=100, type=Repository
Hybrid search: cosine + filters
Returned: exact matches with stars >= 100`}</pre>
              </div>
            </div>
          )}
          {activeTab === 'filters' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div>
                <h3 className="text-xl font-bold">Filter-only mode</h3>
                <p className="mt-2 text-slate-300">Exact attribute filters (batch, industry, roles, location, stars) return all matches — no % scores, no recommendations.</p>
                <ul className="mt-4 space-y-2 text-slate-200">
                  <li className="flex items-center gap-2"><Filter size={16} className="text-indigo-400" /> Batch: W24, S23, etc.</li>
                  <li className="flex items-center gap-2"><Filter size={16} className="text-indigo-400" /> Industry + aliases</li>
                </ul>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
                <pre className="text-xs text-slate-200 whitespace-pre-wrap">{`Query: "YC W24 companies"
Parsed: batch = ["winter 2024", "w24"]
Cypher: WHERE toLower(c.batch) CONTAINS any(token)
Response: Found 253 results (filter_only=true)`}</pre>
              </div>
            </div>
          )}
          {activeTab === 'graph' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div>
                <h3 className="text-xl font-bold">Graph-enabled search</h3>
                <p className="mt-2 text-slate-300">We traverse founders, investors, industries, and repositories to discover related entities and insights.</p>
                <ul className="mt-4 space-y-2 text-slate-200">
                  <li className="flex items-center gap-2"><Network size={16} className="text-indigo-400" /> Expand via relationships</li>
                  <li className="flex items-center gap-2"><Share2 size={16} className="text-indigo-400" /> Summarize with context</li>
                </ul>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
                <pre className="text-xs text-slate-200 whitespace-pre-wrap">{`MATCH (p:Person)-[:FOUNDED]->(c:Company)-[:IN_INDUSTRY]->(i:Industry)
WHERE i.name IN ['developer tools']
RETURN p, c LIMIT 10`}</pre>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Companies carousel */}
      <section className="mx-auto max-w-7xl px-6 pb-20">
        <h3 className="mb-4 text-xl font-bold">Companies you can discover</h3>
        <div ref={carouselRef} className="flex gap-4 overflow-x-auto scroll-smooth">
          {/* doubled list for seamless loop */}
          {([
            { name: 'Zep AI', batch: 'W24', industry: 'B2B', location: 'San Francisco', blurb: 'Memory infrastructure for AI.' },
            { name: '14.ai', batch: 'W24', industry: 'Infrastructure', location: 'San Francisco', blurb: 'Customer support for 1000x teams.' },
            { name: 'DeepDocs', batch: 'S23', industry: 'Developer Tools', location: 'Remote', blurb: 'Docs that answer back.' },
            { name: 'GraphHub', batch: 'W23', industry: 'Data', location: 'NYC', blurb: 'Unified graph for your org.' },
            { name: 'FinSage', batch: 'S22', industry: 'Fintech', location: 'London', blurb: 'AI underwriting for SMBs.' },
            { name: 'Zep AI', batch: 'W24', industry: 'B2B', location: 'San Francisco', blurb: 'Memory infrastructure for AI.' },
            { name: '14.ai', batch: 'W24', industry: 'Infrastructure', location: 'San Francisco', blurb: 'Customer support for 1000x teams.' },
            { name: 'DeepDocs', batch: 'S23', industry: 'Developer Tools', location: 'Remote', blurb: 'Docs that answer back.' },
            { name: 'GraphHub', batch: 'W23', industry: 'Data', location: 'NYC', blurb: 'Unified graph for your org.' },
            { name: 'FinSage', batch: 'S22', industry: 'Fintech', location: 'London', blurb: 'AI underwriting for SMBs.' },
          ] as Array<{name:string; batch:string; industry:string; location:string; blurb:string}>).map((c, i) => (
            <div key={i} className="min-w-[260px] rounded-2xl border border-white/10 bg-white/[0.06] p-4 shadow-md backdrop-blur">
              <div className="text-sm text-indigo-300">YC {c.batch}</div>
              <div className="mt-1 text-lg font-semibold">{c.name}</div>
              <div className="mt-1 text-slate-300 text-sm">{c.industry} • {c.location}</div>
              <p className="mt-2 text-slate-300 text-sm">{c.blurb}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Glow-follow window */}
      <section className="mx-auto max-w-7xl px-6 pb-20">
        <h3 className="mb-4 text-xl font-bold">How it works</h3>
        <div
          className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl"
          onMouseMove={(e) => {
            const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
            setCursorPos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
          }}
          style={{ backgroundImage: `radial-gradient(600px at ${cursorPos.x}px ${cursorPos.y}px, rgba(99,102,241,0.15), transparent 40%)` }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div className="space-y-3">
              {[{ icon: <Search size={16} />, title: 'Understand intent', desc: 'Parse query, extract filters.' },
                { icon: <Filter size={16} />, title: 'Apply filters', desc: 'Batch, industry, location, stars.' },
                { icon: <Network size={16} />, title: 'Traverse graph', desc: 'Follow founders/investors/industry.' },
                { icon: <Share2 size={16} />, title: 'Generate insights', desc: 'Summarize with references.' },].map((s, idx) => (
                <div key={idx} className={`flex items-start gap-3 rounded-xl border p-3 transition ${idx===stepIndex ? 'border-indigo-400/30 bg-indigo-500/10' : 'border-white/10 bg-white/5'}`}>
                  <div className={`${idx===stepIndex ? 'text-indigo-300' : 'text-slate-400'}`}>{s.icon}</div>
                  <div>
                    <div className="font-semibold">{s.title}</div>
                    <div className="text-sm text-slate-300">{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
              <div className="text-xs text-slate-300">Sample workflow</div>
              <div className="mt-2 grid grid-cols-4 gap-2 text-center">
                {[{ icon: <Search size={16} />, title: 'Understand intent' }, { icon: <Filter size={16} />, title: 'Apply filters' }, { icon: <Network size={16} />, title: 'Traverse graph' }, { icon: <Share2 size={16} />, title: 'Generate insights' }].map((s, idx) => (
                  <div key={idx} className={`rounded-lg p-3 ${idx===stepIndex ? 'bg-indigo-600 text-white' : 'bg-white/5 text-slate-300'}`}>
                    <div className="mx-auto mb-1 w-6 h-6 flex items-center justify-center rounded-md bg-white/10">{s.icon}</div>
                    <div className="text-[11px] leading-tight">{s.title}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Scroll overlay experience */}
      <section className="mx-auto max-w-7xl px-6 pb-32">
        <div className="relative" style={{ minHeight: 600 }}>
          <div ref={overlayRef1} className={`absolute inset-0 transition-opacity duration-500 ${overlayActive==='one' ? 'opacity-100 z-20' : 'opacity-0 z-10'}`}>
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-900/40 to-purple-900/30 p-8 shadow-xl">
              <h4 className="text-2xl font-bold">Pipeline-ready data</h4>
              <p className="mt-2 text-slate-300">Ingest companies, founders, investors, and repositories. Enrich with embeddings and relationships.</p>
              <ul className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2 text-slate-200">
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Neo4j-native schema</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Vector indexes for fast recall</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Role-specific relationships</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Alias-aware filters</li>
              </ul>
            </div>
          </div>
          <div ref={overlayRef2} className={`absolute inset-0 transition-opacity duration-500 ${overlayActive==='two' ? 'opacity-100 z-30' : 'opacity-0 z-10'}`}>
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-blue-900/40 to-rose-900/30 p-8 shadow-xl">
              <h4 className="text-2xl font-bold">Actionable intelligence</h4>
              <p className="mt-2 text-slate-300">Summarize direct matches and graph-discovered context into clear, actionable insights.</p>
              <ul className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2 text-slate-200">
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Natural language responses</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Visual graph previews</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> Exact-match recommendations</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="text-emerald-400" size={16} /> No drift in filter-only mode</li>
              </ul>
            </div>
          </div>
          <div className="h-[800px]"></div>
        </div>
      </section>
    </main>
  )
}


