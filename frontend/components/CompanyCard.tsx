'use client'

import { Company } from '@/lib/types'
import { Building2, MapPin, Globe, Tag } from 'lucide-react'

interface CompanyCardProps {
  company: Company
  onClick: () => void
}

export default function CompanyCard({ company, onClick }: CompanyCardProps) {
  const { metadata } = company
  const matchScore = Math.round(company.score * 100)

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow cursor-pointer p-6 space-y-4"
    >
      <div className="flex justify-between items-start">
        <h3 className="text-xl font-semibold text-gray-800 line-clamp-1">
          {metadata.name}
        </h3>
        <span className="text-sm font-medium px-2 py-1 bg-green-100 text-green-800 rounded">
          {matchScore}% match
        </span>
      </div>

      {metadata.description && (
        <p className="text-gray-600 line-clamp-2">{metadata.description}</p>
      )}

      <div className="space-y-2">
        {metadata.batch && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Building2 size={16} />
            <span>YC {metadata.batch}</span>
          </div>
        )}

        {metadata.location && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <MapPin size={16} />
            <span>{metadata.location}</span>
          </div>
        )}

        {metadata.website && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Globe size={16} />
            <span className="truncate">{metadata.website}</span>
          </div>
        )}

        {metadata.industries && metadata.industries.length > 0 && (
          <div className="flex items-start gap-2">
            <Tag size={16} className="text-gray-500 mt-0.5" />
            <div className="flex flex-wrap gap-1">
              {metadata.industries.slice(0, 3).map((industry, idx) => (
                <span
                  key={idx}
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded"
                >
                  {industry}
                </span>
              ))}
              {metadata.industries.length > 3 && (
                <span className="text-xs text-gray-500">
                  +{metadata.industries.length - 3}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}