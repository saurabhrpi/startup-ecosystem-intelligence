'use client'

import RepositoryCard from './RepositoryCard'

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

interface RepositoryGridProps {
  repositories: Repository[]
  onSelectRepository?: (repository: Repository) => void
}

export default function RepositoryGrid({ repositories = [], onSelectRepository }: RepositoryGridProps) {
  if (!repositories || repositories.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No repositories found. Try a different search query.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {repositories.map((repository) => (
        <RepositoryCard
          key={repository.id}
          repository={repository}
          onClick={() => onSelectRepository?.(repository)}
        />
      ))}
    </div>
  )
}