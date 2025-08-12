'use client'

import { Star, GitBranch, Building2 } from 'lucide-react'

interface Repository {
  id: string
  name: string
  description?: string
  stars?: number
  language?: string
  owner?: string
  url?: string
  company?: {
    name: string
    id: string
  }
  company_relationship?: {
    confidence: number
    method: string
  }
}

interface RepositoryCardProps {
  repository: Repository
  onClick?: () => void
}

export default function RepositoryCard({ repository, onClick }: RepositoryCardProps) {
  return (
    <div
      className="bg-white rounded-lg shadow-md p-6 hover:shadow-xl transition-shadow cursor-pointer border border-gray-200"
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-gray-900 truncate flex items-center gap-2">
          <GitBranch className="text-gray-600" size={18} />
          {repository.name}
        </h3>
        {repository.stars && (
          <div className="flex items-center gap-1 text-yellow-600">
            <Star size={16} fill="currentColor" />
            <span className="text-sm font-medium">{repository.stars.toLocaleString()}</span>
          </div>
        )}
      </div>
      
      {repository.description && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{repository.description}</p>
      )}
      
      <div className="flex flex-wrap gap-2 mb-3">
        {repository.language && (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
            {repository.language}
          </span>
        )}
        {repository.owner && (
          <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
            @{repository.owner}
          </span>
        )}
      </div>
      
      {repository.company && (
        <div className="border-t pt-3 mt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 size={14} className="text-gray-500" />
              <span className="text-sm font-medium text-gray-700">
                {repository.company.name}
              </span>
            </div>
            {repository.company_relationship && (
              <span className={`text-xs px-2 py-1 rounded-full ${
                repository.company_relationship.confidence >= 0.95 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-yellow-100 text-yellow-700'
              }`}>
                {Math.round(repository.company_relationship.confidence * 100)}% match
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}