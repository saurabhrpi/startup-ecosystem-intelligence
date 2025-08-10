'use client'

import { useState } from 'react'
import { Search, Sparkles, Command, TrendingUp, Building2 } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string) => void
}

export default function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [isFocused, setIsFocused] = useState(false)

  const normalizeBatchAbbreviation = (text: string): string => {
    // Convert patterns like "YC W24" -> "YC Winter 2024", "YC S23" -> "YC Summer 2023"
    // Also handle without leading YC
    const re = /(yc\s+)?([ws])\s*'?\s*(20)?(\d{2})/i
    return text.replace(re, (_m, _yc, season, _yearPrefix, year2) => {
      const fullYear = `20${year2}`
      const seasonWord = season.toLowerCase() === 'w' ? 'Winter' : 'Summer'
      const ycPrefix = _yc ? 'YC ' : ''
      return `${ycPrefix}${seasonWord} ${fullYear}`
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(normalizeBatchAbbreviation(query))
    }
  }

  const suggestions = [
    { icon: TrendingUp, text: 'AI startups in Series A', color: 'text-green-600' },
    { icon: Building2, text: 'YC W24 companies', color: 'text-blue-600' },
    { icon: Sparkles, text: 'Fintech founders from Stanford', color: 'text-purple-600' },
    { icon: Command, text: 'Developer tools with >100 stars', color: 'text-orange-600' },
    { icon: Command, text: 'Founders in Boston', color: 'text-blue-600' },
    { icon: Command, text: 'Investors in fintech', color: 'text-green-600' },
  ]

  const handleSuggestionClick = (text: string) => {
    const normalized = normalizeBatchAbbreviation(text)
    setQuery(normalized)
    onSearch(normalized)
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="relative">
        {/* Search Input Container */}
        <div className={`relative transition-all duration-300 ${isFocused ? 'scale-105' : ''}`}>
          {/* Gradient Background */}
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-20"></div>
          
          {/* Search Input */}
          <div className="relative bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            <div className="flex items-center">
              <div className="pl-6">
                <Search className={`transition-colors ${isFocused ? 'text-indigo-600' : 'text-gray-400'}`} size={24} />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder="Search for startups, industries, technologies, or founders..."
                className="flex-1 px-4 py-5 text-lg text-gray-800 placeholder-gray-400 focus:outline-none"
              />
              <button
                type="submit"
                className="mr-3 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl hover:shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center gap-2"
              >
                <Sparkles size={18} />
                <span>Discover</span>
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Suggestion Pills */}
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        {suggestions.map((suggestion, idx) => {
          const Icon = suggestion.icon
          return (
            <button
              key={idx}
              onClick={() => handleSuggestionClick(suggestion.text)}
              className="group flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-all duration-200 shadow-sm hover:shadow-md"
            >
              <Icon className={`${suggestion.color} group-hover:scale-110 transition-transform`} size={16} />
              <span className="text-sm text-gray-700 group-hover:text-indigo-700 font-medium">
                {suggestion.text}
              </span>
            </button>
          )
        })}
      </div>

      {/* Quick Stats */}
      <div className="mt-6 flex justify-center items-center gap-6 text-sm text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>Live data</span>
        </div>
        <div className="flex items-center gap-1">
          <Search size={14} />
          <span>Graph-RAG powered</span>
        </div>
        <div className="flex items-center gap-1">
          <Sparkles size={14} />
          <span>AI-enhanced results</span>
        </div>
      </div>
    </div>
  )
}