'use client'

import { User2, Briefcase, MapPin } from 'lucide-react'

interface Person {
  id: string
  score: number
  metadata: {
    name: string
    role?: string
    company?: string
    source?: string
    location?: string
    type: string
  }
}

export default function InvestorCard({ person, onClick }: { person: Person; onClick?: () => void }) {
  const { metadata } = person
  const matchScore = Math.round(person.score * 100)

  return (
    <div
      onClick={onClick}
      onDoubleClick={onClick}
      className="group relative bg-white rounded-xl shadow-sm hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden border border-gray-100 hover:border-indigo-200"
    >
      <div className="relative p-6 space-y-4">
        <div className="flex justify-between items-start">
          <div className="flex-1 pr-2">
            <div className="flex items-center gap-2">
              <User2 className="text-gray-700" size={18} />
              <h3 className="text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                {metadata.name}
              </h3>
            </div>
            {(
              metadata.role || metadata.company
            ) && (
              <div className="mt-1 text-sm text-gray-600 flex flex-wrap gap-3">
                <span className="inline-flex items-center gap-1">
                  <Briefcase size={14} className="text-indigo-500" /> {metadata.role || 'Investor'}
                </span>
              </div>
            )}
          </div>
          <div className="px-3 py-1 rounded-full text-sm font-bold bg-gradient-to-r from-blue-400 to-indigo-500 text-white shadow-sm">
            {matchScore}%
          </div>
        </div>

        {metadata.location && (
          <div className="flex items-center gap-1.5 text-sm text-gray-600">
            <MapPin className="text-red-500" size={14} />
            <span className="truncate">{metadata.location}</span>
          </div>
        )}
      </div>
    </div>
  )
}


