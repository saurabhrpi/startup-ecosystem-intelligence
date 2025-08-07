'use client'

import { Company } from '@/lib/types'
import { Building2, MapPin, Globe, Tag, TrendingUp, Calendar, Users, ArrowUpRight } from 'lucide-react'

interface CompanyCardProps {
  company: Company
  onClick: () => void
}

export default function CompanyCard({ company, onClick }: CompanyCardProps) {
  const { metadata } = company
  const matchScore = Math.round(company.score * 100)

  // Determine score color based on value
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-gradient-to-r from-green-400 to-emerald-500 text-white'
    if (score >= 60) return 'bg-gradient-to-r from-blue-400 to-indigo-500 text-white'
    if (score >= 40) return 'bg-gradient-to-r from-yellow-400 to-orange-500 text-white'
    return 'bg-gradient-to-r from-gray-400 to-gray-500 text-white'
  }

  // Get industry color
  const getIndustryColor = (index: number) => {
    const colors = [
      'bg-blue-100 text-blue-700 border-blue-200',
      'bg-purple-100 text-purple-700 border-purple-200',
      'bg-green-100 text-green-700 border-green-200',
      'bg-yellow-100 text-yellow-700 border-yellow-200',
      'bg-pink-100 text-pink-700 border-pink-200',
    ]
    return colors[index % colors.length]
  }

  return (
    <div
      onClick={onClick}
      className="group relative bg-white rounded-xl shadow-sm hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden border border-gray-100 hover:border-indigo-200"
    >
      {/* Gradient Border Effect on Hover */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 opacity-0 group-hover:opacity-10 transition-opacity duration-300"></div>
      
      {/* Card Content */}
      <div className="relative p-6 space-y-4">
        {/* Header with Score */}
        <div className="flex justify-between items-start">
          <div className="flex-1 pr-2">
            <h3 className="text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
              {metadata.name}
            </h3>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-bold ${getScoreColor(matchScore)} shadow-sm`}>
            {matchScore}%
          </div>
        </div>

        {/* Description */}
        {metadata.description && (
          <p className="text-gray-600 line-clamp-2 text-sm leading-relaxed">
            {metadata.description}
          </p>
        )}

        {/* Quick Info Grid */}
        <div className="grid grid-cols-2 gap-2">
          {metadata.batch && (
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <Calendar className="text-indigo-500" size={14} />
              <span className="font-medium">YC {metadata.batch}</span>
            </div>
          )}

          {metadata.location && (
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <MapPin className="text-red-500" size={14} />
              <span className="truncate">{metadata.location}</span>
            </div>
          )}

          {metadata.team_size && (
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <Users className="text-green-500" size={14} />
              <span>{metadata.team_size} people</span>
            </div>
          )}

          {metadata.status && (
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <TrendingUp className="text-purple-500" size={14} />
              <span className="capitalize">{metadata.status}</span>
            </div>
          )}
        </div>

        {/* Industries Tags */}
        {metadata.industries && metadata.industries.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {metadata.industries.slice(0, 3).map((industry, idx) => (
              <span
                key={idx}
                className={`text-xs px-2.5 py-1 rounded-full border font-medium ${getIndustryColor(idx)}`}
              >
                {industry}
              </span>
            ))}
            {metadata.industries.length > 3 && (
              <span className="text-xs px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full">
                +{metadata.industries.length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Website Link */}
        {metadata.website && (
          <div className="pt-3 border-t border-gray-100">
            <div className="flex items-center justify-between group/link">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Globe size={14} />
                <span className="truncate max-w-[180px]">{metadata.website}</span>
              </div>
              <ArrowUpRight 
                size={14} 
                className="text-gray-400 group-hover/link:text-indigo-600 transition-colors" 
              />
            </div>
          </div>
        )}

        {/* Hover Overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 to-purple-600 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
      </div>
    </div>
  )
}