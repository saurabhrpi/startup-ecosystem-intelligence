'use client'

import PersonCard from './PersonCard'

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

export default function PersonGrid({ people = [], onSelectPerson }: { people: Person[]; onSelectPerson?: (p: Person) => void }) {
  if (!people || people.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">No people found. Try a different search query.</div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {people.map((person) => (
        <PersonCard key={person.id} person={person} onClick={() => onSelectPerson?.(person)} />
      ))}
    </div>
  )
}


