'use client'

import { User2, Briefcase, Building2, MapPin, BookmarkPlus, Check } from 'lucide-react'
import { useState } from 'react'

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

export default function PersonCard({ person, onClick, suppressScore }: { person: Person; onClick?: () => void; suppressScore?: boolean }) {
  const { metadata } = person
  const matchScore = Math.round(person.score * 100)
  const [isFollowing, setIsFollowing] = useState(false)
  const [isFollowLoading, setIsFollowLoading] = useState(false)
  
  return (
    <div
      onClick={onClick}
      onDoubleClick={onClick}
      className="group relative bg-white rounded-xl shadow-sm hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden border border-gray-100 hover:border-indigo-200"
    >
      <div className="relative p-6 space-y-4">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex-1 pr-2">
            <div className="flex items-center gap-2">
              <User2 className="text-gray-700" size={18} />
              <h3 className="text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                {metadata.name}
              </h3>
            </div>
            {(metadata.role || metadata.company) && (
              <div className="mt-1 text-sm text-gray-600 flex flex-wrap gap-3">
                {metadata.role && (
                  <span className="inline-flex items-center gap-1">
                    <Briefcase size={14} className="text-indigo-500" /> {metadata.role}
                  </span>
                )}
                {metadata.company && (
                  <span className="inline-flex items-center gap-1">
                    <Building2 size={14} className="text-green-600" /> {metadata.company}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              className={`${isFollowing ? 'bg-green-50 text-green-700 hover:bg-green-100' : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'} inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold`}
              onClick={async (e) => {
                e.stopPropagation()
                if (isFollowing || isFollowLoading) return
                try {
                  setIsFollowLoading(true)
                  const res = await fetch('/api/user/follow', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ entity_id: person.id }) })
                  if (res.ok) {
                    setIsFollowing(true)
                  } else if (res.status === 401) {
                    alert('Please sign in to follow')
                  } else {
                    const txt = await res.text().catch(() => '')
                    console.error('Follow failed', res.status, txt)
                    alert('Could not follow. Please try again.')
                  }
                } catch (err) {
                  console.error('Follow error', err)
                  alert('Could not follow. Please try again.')
                } finally {
                  setIsFollowLoading(false)
                }
              }}
              aria-label={isFollowing ? 'Following person' : 'Follow person'}
              title={isFollowing ? 'Following' : 'Follow person'}
              disabled={isFollowLoading || isFollowing}
            >
              {isFollowing ? <Check size={14} /> : <BookmarkPlus size={14} />} {isFollowing ? 'Following' : (isFollowLoading ? 'Following…' : 'Follow')}
            </button>
            {!suppressScore && (
              <div className="px-3 py-1 rounded-full text-sm font-bold bg-gradient-to-r from-blue-400 to-indigo-500 text-white shadow-sm">
                {matchScore}%
              </div>
            )}
          </div>
        </div>

        {/* Location */}
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


