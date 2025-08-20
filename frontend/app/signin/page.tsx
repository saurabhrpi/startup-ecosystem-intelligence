'use client'

import { useState } from 'react'
import { signIn } from 'next-auth/react'
import { Sparkles, Mail, Shield, CheckCircle2, ArrowRight } from 'lucide-react'

export default function SignInPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const res = await signIn('credentials', { email, redirect: true, callbackUrl: '/' })
    if (res?.error) setError('Sign-in failed')
    setLoading(false)
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Background accents */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-1/2 -translate-x-1/2 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-blob animation-delay-4000"></div>
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
            <h1 className="mt-4 text-4xl md:text-5xl font-extrabold tracking-tight text-gray-900">
              Discover opportunities in the startup ecosystem
            </h1>
            <p className="mt-4 text-gray-600 max-w-xl">
              Search companies, founders, investors, and repositories with precise filters for batch, industry, and location. No noise—just accurate matches.
            </p>
            <ul className="mt-6 space-y-3 text-gray-700">
              <li className="flex items-start gap-2"><CheckCircle2 className="text-green-600 mt-0.5" size={18} /> Filter-only results return exact matches—no drift.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="text-green-600 mt-0.5" size={18} /> Recommendations derive strictly from real matches.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="text-green-600 mt-0.5" size={18} /> Visualize connections across people, companies, and repos.</li>
            </ul>
          </div>

          {/* Right: sign-in card */}
          <div className="w-full">
            <div className="relative mx-auto w-full max-w-md">
              <div className="absolute -inset-0.5 rounded-3xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-30 blur-lg"></div>
              <div className="relative rounded-3xl border border-gray-100 bg-white/90 shadow-xl backdrop-blur-sm p-8">
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-gray-800">Sign in</h2>
                  <p className="mt-1 text-sm text-gray-600">Use your email to continue</p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Email</label>
                    <div className="relative">
                      <div className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-gray-400">
                        <Mail size={16} />
                      </div>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full rounded-xl border border-gray-200 bg-white px-10 py-3 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                        placeholder="you@example.com"
                      />
                    </div>
                  </div>
                  {error && <p className="text-sm text-red-600">{error}</p>}
                  <button
                    type="submit"
                    disabled={loading}
                    className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50"
                  >
                    {loading ? 'Signing in…' : 'Continue'}
                    <ArrowRight size={16} className="transition group-hover:translate-x-0.5" />
                  </button>
                </form>
                <p className="mt-4 text-xs text-gray-500">
                  By continuing, you agree to our Terms and Privacy Policy.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}


