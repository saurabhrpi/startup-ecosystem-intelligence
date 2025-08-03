'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string) => void
}

export default function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for startups, industries, or technologies..."
          className="w-full px-6 py-4 pr-12 text-lg text-gray-800 bg-white rounded-full border-2 border-gray-200 focus:border-primary focus:outline-none shadow-lg"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 transform -translate-y-1/2 p-3 bg-primary text-white rounded-full hover:bg-orange-600 transition-colors"
        >
          <Search size={24} />
        </button>
      </div>
      <div className="mt-4 text-center">
        <span className="text-sm text-gray-500">
          Try: "AI startups", "fintech San Francisco", "developer tools", "YC W23"
        </span>
      </div>
    </form>
  )
}