'use client'

import { X, Star, GitBranch, ExternalLink, Building2, Shield } from 'lucide-react'

type RepoCompany = {
  id: string
  name: string
}

type RepoRelationship = {
  confidence: number
  method: string
}

type RepoItem = {
  id: string
  name: string
  description?: string
  stars?: number
  language?: string
  owner?: string
  url?: string
  company?: RepoCompany
  company_relationship?: RepoRelationship
}

export default function RepositoryDetail({ repository, onClose }: { repository: RepoItem; onClose: () => void }) {
  if (!repository) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <GitBranch className="text-gray-700" size={20} />
              <h2 className="text-2xl font-bold text-gray-900">{repository.name}</h2>
            </div>
            {repository.owner && (
              <div className="text-sm text-gray-500">@{repository.owner}</div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 text-gray-600"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Meta */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {typeof repository.stars === 'number' && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-yellow-100 text-yellow-700 text-xs">
              <Star size={14} /> {repository.stars.toLocaleString()} stars
            </span>
          )}
          {repository.language && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-blue-100 text-blue-700 text-xs">
              {repository.language}
            </span>
          )}
          {repository.company_relationship && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs">
              <Shield size={14} /> {Math.round(repository.company_relationship.confidence * 100)}% match
            </span>
          )}
        </div>

        {/* Description */}
        {repository.description && (
          <p className="text-gray-700 leading-relaxed mb-4">{repository.description}</p>
        )}

        {/* Company association */}
        {repository.company ? (
          <div className="border rounded-xl p-4 mb-4">
            <div className="flex items-center gap-2 mb-1">
              <Building2 size={16} className="text-gray-600" />
              <span className="text-sm text-gray-600">Likely owned by</span>
            </div>
            <div className="text-gray-900 font-semibold">{repository.company.name}</div>
            <div className="text-xs text-gray-500">ID: {repository.company.id}</div>
          </div>
        ) : (
          <div className="text-sm text-gray-500 mb-4">No associated company found.</div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-400">Repository ID: {repository.id}</div>
          {repository.url && (
            <a
              href={repository.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-gray-900 text-white hover:bg-gray-800"
            >
              <ExternalLink size={14} /> View on GitHub
            </a>
          )}
        </div>
      </div>
    </div>
  )
}


