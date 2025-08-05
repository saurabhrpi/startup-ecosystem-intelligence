'use client'

import { useState } from 'react'
import SearchBar from '@/components/SearchBar'
import CompanyGrid from '@/components/CompanyGrid'
import CompanyDetail from '@/components/CompanyDetail'
import { Company, SearchResult } from '@/lib/types'

export default function Home() {
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async (query: string) => {
    setLoading(true)
    try {
      const response = await fetch(`/api/backend/search?query=${encodeURIComponent(query)}&top_k=20&filter_type=company`, {
        headers: {
          'ngrok-skip-browser-warning': 'true',
          'Accept': 'application/json',
        },
      })
      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`)
      }
      const data = await response.json()
      console.log('Search response:', data) // Debug log
      setSearchResults(data)
      setSelectedCompany(null)
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults({
        query: query,
        matches: [],
        response: 'Error connecting to the search service. Please try again.',
        total_results: 0
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-4">
            Startup Ecosystem Intelligence
          </h1>
          <p className="text-xl text-gray-600">
            AI-powered discovery and analysis of {new Intl.NumberFormat().format(2485)} startups
          </p>
        </header>

        <SearchBar onSearch={handleSearch} />

        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        )}

        {searchResults && !loading && (
          <div className="mt-12">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-center mb-4">
                Found {searchResults.total_results} results
              </h2>
              {searchResults.response && (
                <div className="max-w-3xl mx-auto text-center">
                  <p className="text-gray-600 italic">{searchResults.response}</p>
                </div>
              )}
            </div>

            <CompanyGrid 
              companies={searchResults.matches} 
              onSelectCompany={setSelectedCompany}
            />
          </div>
        )}

        {selectedCompany && (
          <CompanyDetail 
            company={selectedCompany} 
            onClose={() => setSelectedCompany(null)}
          />
        )}
      </div>
    </main>
  )
}