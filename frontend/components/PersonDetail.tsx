'use client'

import { useEffect } from 'react'
import { X, Briefcase, Building2, MapPin } from 'lucide-react'

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

export default function PersonDetail({ person, onClose }: { person: Person; onClose: () => void }) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-start">
          <div>
            <h2 className="text-3xl font-bold text-gray-800 break-words">{person.metadata.name}</h2>
            {person.metadata.role && (
              <div className="mt-2 text-gray-700 flex items-center gap-2">
                <Briefcase size={16} className="text-indigo-600" /> {person.metadata.role}
              </div>
            )}
            {person.metadata.company && (
              <div className="mt-1 text-gray-700 flex items-center gap-2">
                <Building2 size={16} className="text-green-600" /> {person.metadata.company}
              </div>
            )}
            {person.metadata.location && (
              <div className="mt-1 text-gray-700 flex items-center gap-2">
                <MapPin size={16} className="text-red-500" /> {person.metadata.location}
              </div>
            )}
          </div>
          <button onClick={onClose} className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-full transition-all">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="text-sm text-gray-500">Match score: {(Math.round(person.score * 100))}%</div>
          {person.metadata.source && (
            <div className="text-sm text-gray-500">Source: {person.metadata.source}</div>
          )}
        </div>
      </div>
    </div>
  )
}


