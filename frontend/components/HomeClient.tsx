'use client'

import { useState, useEffect } from 'react'
import SearchBar from '@/components/SearchBar'
import CompanyGrid from '@/components/CompanyGrid'
import RepositoryGrid from '@/components/RepositoryGrid'
import RepositoryDetail from '@/components/RepositoryDetail'
import CompanyDetail from '@/components/CompanyDetail'
import ResponseDisplay from '@/components/ResponseDisplay'
import { Company, SearchResult } from '@/lib/types'
import { TrendingUp, Sparkles, Zap } from 'lucide-react'
import PersonGrid from '@/components/PersonGrid'
import InvestorGrid from '@/components/InvestorGrid'

type Stats = { total_companies: number; total_embeddings: number; data_sources: number }

export default function HomeClient({ initialStats }: { initialStats: Stats }) {
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [selectedRepository, setSelectedRepository] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<Stats>(initialStats)

  // Fetch stats on component mount
  useEffect(() => {
    // Optionally refresh stats on mount; keeps UI consistent on first paint
    const refreshStats = async () => {
      try {
        const response = await fetch('/api/backend/ecosystem-stats', {
          headers: { Accept: 'application/json' },
        })
        if (response.ok) {
          const data = await response.json()
          setStats((prev) => (JSON.stringify(prev) === JSON.stringify(data) ? prev : data))
        }
      } catch (error) {
        console.error('Error fetching stats:', error)
      }
    }
    refreshStats()
  }, [])

  const handleSearch = async (query: string) => {
    setLoading(true)
    try {
      const ql = (query || '').toLowerCase()
      const isInvestorQuery = ['investor', 'investors', 'vc', 'venture'].some(t => ql.includes(t))
      const params = new URLSearchParams({
        query,
        top_k: '5',
      })
      if (isInvestorQuery) {
        params.set('filter_type', 'person')
        params.set('person_roles', 'investor')
      }
      const response = await fetch(`/api/search?${params.toString()}`, { headers: { Accept: 'application/json' } })
      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`)
      }
      const data = await response.json()
      setSearchResults(data)
      setSelectedCompany(null)
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults({
        query,
        matches: [],
        response: 'Error connecting to the search service. Please try again.',
        total_results: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="container mx-auto px-4 py-8 relative">
        {/* Header */}
        <header className="text-center mb-12">
          <div className="inline-flex items-center justify-center space-x-2 mb-4 bg-gradient-to-r from-blue-100 to-indigo-100 px-4 py-2 rounded-full">
            <Zap className="text-indigo-600" size={20} />
            <span className="text-sm font-semibold text-indigo-700">Graph-RAG Powered Intelligence</span>
          </div>

          <h1 className="text-6xl font-bold mb-4">
            <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Startup Ecosystem
            </span>
            <br />
            <span className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              Intelligence Platform
            </span>
          </h1>

          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Discover hidden connections and opportunities across{' '}
            <span className="font-semibold text-gray-800 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              {stats.total_companies > 0 ? new Intl.NumberFormat().format(stats.total_companies) : '5,000+'}
            </span>{' '}
            startups using advanced AI analysis
          </p>

          {/* Stats Row */}
          <div className="flex justify-center items-center space-x-8 mt-8">
            <div className="flex items-center space-x-2">
              <TrendingUp className="text-green-500" size={20} />
              <span className="text-sm text-gray-600">
                <span className="font-bold text-gray-800">
                  {stats.total_embeddings > 0 ? `${(stats.total_embeddings / 1000).toFixed(0)}K+` : '15K+'}
                </span>{' '}
                Embeddings
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <Sparkles className="text-purple-500" size={20} />
              <span className="text-sm text-gray-600">
                <span className="font-bold text-gray-800">{stats.data_sources}</span> Data Sources
              </span>
            </div>
          </div>
        </header>

        {/* Search Section */}
        <div className="max-w-3xl mx-auto mb-12">
          <SearchBar onSearch={handleSearch} />
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col justify-center items-center py-20">
            <div className="relative">
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-indigo-200"></div>
              <div className="absolute top-0 animate-spin rounded-full h-16 w-16 border-t-4 border-indigo-600"></div>
            </div>
            <p className="mt-4 text-gray-600 animate-pulse">Analyzing ecosystem intelligence...</p>
          </div>
        )}

        {/* Results Section */}
        {searchResults && !loading && (
          <div className="space-y-8">
            {/* Response Display */}
            {searchResults.response && (
              <ResponseDisplay response={searchResults.response} totalResults={searchResults.total_results} matches={searchResults.matches as any[]} query={searchResults.query} />
            )}

            {/* Results Grid - Companies or Repositories */}
              {searchResults.matches && searchResults.matches.length > 0 && (
              <div>
                {(() => {
                  // Determine result type based on first match structure
                  const firstMatch: any = searchResults.matches[0]
                  const resultType = firstMatch?.type || (firstMatch?.metadata?.type) || 'Company'
                  const isRepository = resultType === 'Repository'
                  const isPerson = resultType === 'Person'
                  const isInvestorList = isPerson && (searchResults.matches as any[]).some((m:any) => {
                    const role = (m?.metadata?.role || '').toLowerCase()
                    return role.includes('investor') || role.includes('vc') || role.includes('venture')
                  })
                    
                  return (
                    <>
                      <div className="text-center mb-6">
                        <h2 className="text-3xl font-bold text-gray-800 mb-2">
                          {isRepository ? 'Discovered Repositories' : (isPerson ? (isInvestorList ? 'Discovered Investors' : 'Discovered Founders') : 'Discovered Companies')}
                        </h2>
                        <p className="text-gray-600">
                          {isRepository 
                            ? 'Showing repositories with their associated companies'
                            : isPerson
                              ? (isInvestorList ? 'Showing investors' : 'Showing founders and their associated companies')
                              : 'Click on any company to explore detailed insights'}
                        </p>
                      </div>
                        {isRepository ? (
                          <RepositoryGrid 
                            repositories={searchResults.matches.map((m: any) => m.metadata || m)} 
                            onSelectRepository={(repo) => {
                              setSelectedRepository(repo)
                            }}
                          />
                        ) : isPerson ? (
                          (() => {
                            const peopleOnly = (searchResults.matches as any[]).filter((m) => (m?.type || m?.metadata?.type) === 'Person')
                            const uniquePeople = Array.from(new Map(peopleOnly.map((p) => [p.id, p])).values())
                            if (isInvestorList) {
                              const investors = uniquePeople.filter((p:any) => {
                                const role = (p?.metadata?.role || '').toLowerCase()
                                return role.includes('investor') || role.includes('vc') || role.includes('venture')
                              })
                              return <InvestorGrid people={investors as any} />
                            }
                            return (
                              <PersonGrid 
                                people={uniquePeople as any}
                                onSelectPerson={() => {}}
                              />
                            )
                          })()
                        ) : (
                          <CompanyGrid 
                            companies={searchResults.matches as unknown as Company[]} 
                            onSelectCompany={setSelectedCompany} 
                          />
                        )}
                    </>
                  )
                })()}
              </div>
            )}
          </div>
        )}

        {/* Company Detail Modal */}
        {selectedCompany && (
          <CompanyDetail company={selectedCompany} onClose={() => setSelectedCompany(null)} />
        )}
        {selectedRepository && (
          <RepositoryDetail repository={selectedRepository} onClose={() => setSelectedRepository(null)} />
        )}
      </div>
    </main>
  )
}


